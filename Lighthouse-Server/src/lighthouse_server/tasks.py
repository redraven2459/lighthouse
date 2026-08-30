import threading, traceback
from typing import Any
from datetime import datetime, UTC
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlmodel import Session, select

from lighthouse_server.models import *
from lighthouse_server.database_api import DatabaseAPI


tidal_api_auth_address = "tidal_api_auth_address"
tidekeeeper_api_auth_address = "tidekeeper_api_auth_address"

@dataclass
class TaskThread:
    database_id: int
    thread: Thread

class TaskHandler():
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.interrupt_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.task_threads: dict[int, TaskThread] = {}

    def set_task_complete(self, task_id):
        with Session(DatabaseAPI().engine) as session:
            # Get task
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            # Clear task message
            task.message = ""
            # Set TaskStatusCode to complete
            task.status_code = TaskStatusCode.COMPLETE
            # Set complete time
            task.complete_time = datetime.now(UTC)
            # Write task to db
            session.commit()
        # Remove thread from task_threads
        self.task_threads.pop(task_id)
        return

    def set_task_interrupted(self, task_id):
        with self.interrupt_lock:
            with Session(DatabaseAPI().engine) as session:
                # Get task
                task = session.exec(select(Task).where(Task.id == task_id)).one()
                if task.status_code != TaskStatusCode.INTERRUPTED:
                    # Set task message
                    task.message = ""
                    # Set TaskStatusCode to error
                    task.status_code = TaskStatusCode.INTERRUPTED
                    # Update stdout
                    task.stdout.append("---INTERRUPTED---")
                    # Set complete time
                    task.complete_time = datetime.now(UTC)
                    # Write task to db
                    session.commit()
                    # Remove thread from task_threads
                    #self.task_threads.pop(task_id)
        return

    def set_task_error(self, task_id, e):
        with Session(DatabaseAPI().engine) as session:
            # Get task
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            # Set task message
            task.message = str(e) + "\n" + traceback.format_exc()
            # Set TaskStatusCode to error
            task.status_code = TaskStatusCode.ERROR
            # Set complete time
            task.complete_time = datetime.now(UTC)
            # Write task to db
            session.commit()
        # Remove thread from task_threads
        self.task_threads.pop(task_id)
        return



    def execute_task(self, target, task_id, *args, **kwargs):
        try:
            return target(task_id, *args, **kwargs)
        except Exception as e:
            self.set_task_error(task_id, e)

    def start_task(self, target, *args, description, **kwargs):
        # Add task to DB
        with Session(DatabaseAPI().engine) as session:
            task = Task(description=description, message="Task Starting")
            session.add(task)
            session.commit()
            session.refresh(task)

        # Create and start task thread
        t = threading.Thread(target=self.execute_task, args=(target, task.id, *args), kwargs=kwargs)
        self.task_threads[task.id] = TaskThread(database_id=task.id, thread=t)
        self.task_threads[task.id].thread.start()
        return task.id

    def update_task_status_code(self, task_id, status_code):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            task.status_code = status_code
            session.commit()
            session.refresh(task)

    def update_task_message(self, task_id, message):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            task.message = message
            session.commit()

    def update_task_data(self, task_id, data):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            task.data = data
            session.commit()

    def update_task_data_field(self, task_id, field, data):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            task.data[field] = data
            session.commit()

    def update_task_stdout(self, task_id, line):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            task.stdout.append(line)
            session.commit()
        return

    def get_task_status_code(self, task_id):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            return task.status_code

    def get_task_data_field(self, task_id, field):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            return task.data.get(field)

    def get_task_stdout(self, task_id):
        with Session(DatabaseAPI().engine) as session:
            task = session.exec(select(Task).where(Task.id == task_id)).one()
            return task.stdout

    def startup(self):
        with Session(DatabaseAPI().engine) as session:
            # Check for incomplete JobProcessing entries (i.e: leftover claims from an ungraceful shutdown)
            incomplete_jobs = session.exec(select(JobProcessing)).all()
            if incomplete_jobs != []:
                print("During startup lighthouse_server identified leftover job processing claims from an ungraceful shutdown. The database will need to be repaired.")
                for job in incomplete_jobs:
                    session.delete(job)
                session.commit()
            if incomplete_jobs != []:
                print("Database repair successful")

            # Check for incomplete tasks
            incomplete_tasks = session.exec(select(Task).where((Task.status_code != TaskStatusCode.COMPLETE), (Task.status_code != TaskStatusCode.INTERRUPTED), (Task.status_code != TaskStatusCode.ERROR))).all()
            if len(incomplete_tasks) > 0:
                print("During startup lighthouse_server identified tasks that were interrupted gracelessly. The database will need to be repaired.")
                for task in incomplete_tasks:
                    task.status_code = TaskStatusCode.INTERRUPTED
                session.commit()
                print("Database repair successful")

            # Check for pending tracks
            # TODO: this should be changed to check for pending tracks first to display a message
            tracks = session.exec(select(Track).where(Track.acquisition_state == AcquisitionState.PENDING))
            for track in tracks:
                track.acquisition_state = AcquisitionState.EMPTY
                track.acquisition_quality = None
            session.commit()

            # Check for pending videos
            # TODO: this should be changed to check for pending tracks first to display a message
            videos = session.exec(select(Video).where(Video.acquisition_state == AcquisitionState.PENDING))
            for video in videos:
                video.acquisition_state = AcquisitionState.EMPTY
            session.commit()
        return

    def shutdown(self):
        if self.task_threads != {}:
            # Shutdown threads
            print("Shutting down lighthouse_server worker threads...")
            self.stop_event.set()
            task_thread_len = len(self.task_threads)
            task_thread_i = 1
            for task_key in list(self.task_threads.keys()):
                try:
                    print("Shutting down lighthouse_server worker thread: " + str(task_key) + " (" + str(task_thread_i) + "/" + str(task_thread_len) + ")")
                    task_thread_i = task_thread_i + 1
                    task_thread = self.task_threads[task_key]
                    task_thread.thread.join(timeout=60)
                    if task_thread.thread.is_alive():
                        print("Task thread: " + str(task_key) + " has failed to stop within 60s")
                except RuntimeErorr:
                    pass

            print ("Marking incomplete tasks as interrupted...")
            # Mark incomplete threads as INTERRUPTED
            with Session(DatabaseAPI().engine) as session:
                for task_key in self.task_threads:
                    task_thread = self.task_threads[task_key]
                    task = session.exec(select(Task).where(Task.id == task_thread.database_id)).one()
                    task.status_code = TaskStatusCode.INTERRUPTED
                session.commit()
        return
