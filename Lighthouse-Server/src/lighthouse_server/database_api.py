import os, time, random
from sqlmodel import create_engine, SQLModel, text, Session, select

from lighthouse_server.settings import Settings
from lighthouse_server.models import *

class DatabaseAPI():
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

        # Init DB engine
        self._sqlite_file_path = self.settings.database_path
        self._sqlite_url = f"sqlite:///{self._sqlite_file_path}"
        self.engine = create_engine(self._sqlite_url, connect_args={"timeout": 60})

        # Init DB metadata
        self._prototyping_mode = True
        if self._prototyping_mode:
            SQLModel.metadata.create_all(self.engine)

        # Enable foreign keys
        with self.engine.connect() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))

class DatabaseLock:
    def __init__(self, tidal_id: int, tidal_type: TidalType):
        self.tidal_id: int = tidal_id
        self.tidal_type: TidalType = tidal_type

    def __enter__(self):
        claimed = False
        while claimed == False:
            with Session(DatabaseAPI().engine) as session:
                job = JobProcessing(tidal_id=self.tidal_id, tidal_type=self.tidal_type)
                session.add(job)
                try:
                    session.commit()
                    claimed = True
                except Exception:
                    session.rollback()
                    claimed = False
                    time.sleep(random.uniform(0.4, 0.6))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with Session(DatabaseAPI().engine) as session:
            claim = session.exec(select(JobProcessing).where((JobProcessing.tidal_id == self.tidal_id) & (JobProcessing.tidal_type == self.tidal_type))).one()
            session.delete(claim)
            session.commit()
        return
