import subprocess, threading, os, time, random

from lighthouse_server.settings import Settings
import lighthouse_server.tasks
from lighthouse_server.tasks import TaskHandler, TaskStatusCode, tidekeeeper_api_auth_address

class TidekeeperAPI():
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        if hasattr(self, "_initialized"):
                return
        self._initialized = True
        self.settings = Settings()
        self.tidekeeper_lock = threading.Lock()
        self.nextQueryTime = time.time()

    @staticmethod
    def getBaseTidalUrl():
        return "https://tidal.com/"

    @staticmethod
    def getAlbumLink(album_id):
        return TidekeeperAPI.getBaseTidalUrl() + "album/" + str(album_id)

    @staticmethod
    def getTrackLink(track_id):
        return TidekeeperAPI.getBaseTidalUrl() + "track/" + str(track_id)

    @staticmethod
    def getVideoLink(video_id):
        return TidekeeperAPI.getBaseTidalUrl() + "video/" + str(video_id)

    def popen(self, task_id, runArgs):
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_TIDEKEEPER_LOCK)
        with self.tidekeeper_lock:
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
            if time.time() < self.nextQueryTime:
                time.sleep(self.nextQueryTime - time.time())

            if (self.settings.tidekeeper_path == ""):
                proc = subprocess.Popen(["python", "-m", "tidekeeper", "-c", self.settings.tidekeeper_config_path, *runArgs], stdout=subprocess.PIPE, text=True)
            else:
                proc = subprocess.Popen(["python", self.settings.tidekeeper_path, "-c", self.settings.tidekeeper_config_path, *runArgs], stdout=subprocess.PIPE, text=True)

            for line in proc.stdout:
                status_code = TaskHandler().get_task_status_code(task_id)
                if (status_code == TaskStatusCode.WAITING_FOR_TIDEKEEPER_AUTH) and ("[SUCCESS] AccessToken good" in line):
                    TaskHandler().update_task_data_field(task_id, tidekeeeper_api_auth_address, "")
                    TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)

                if "Waiting for authorization..." in line:
                    last_line = TaskHandler().get_task_stdout(task_id)[-1]
                    auth_url = (last_line.split(" "))[2]
                    TaskHandler().update_task_data_field(task_id, tidekeeeper_api_auth_address, auth_url)
                    TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_TIDEKEEPER_AUTH)

                if "[ERR] No result" in line:
                    temp_string = line.rsplit("[", 1)[-1]
                    temp_string = temp_string.rsplit("]", 1)[0]
                    parts = temp_string.split("/")
                    missing_id = int(parts[-1])
                    not_found_items = TaskHandler().get_task_data_field(task_id, "not_found_items")
                    if not_found_items is None:
                        not_found_items = []
                    not_found_items.append(missing_id)
                    TaskHandler().update_task_data_field(task_id, "not_found_items", not_found_items)

                TaskHandler().update_task_stdout(task_id, line)
            proc.wait()
            self.nextQueryTime = time.time() + random.randint(5, 15)

    def acquireAlbum(self, task_id, album_id):
        self.popen(task_id, ["-l", TidekeeperAPI.getAlbumLink(album_id)])
        return

    def acquireTrack(self, task_id, track_id):
        self.popen(task_id, ["-l", TidekeeperAPI.getTrackLink(track_id)])

    def acquireVideo(self, task_id, video_id):
        self.popen(task_id, ["-l", TidekeeperAPI.getVideoLink(video_id)])
