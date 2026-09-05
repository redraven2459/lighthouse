import os, sys, json, logging
from datetime import datetime

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define settings
class Settings(BaseSettings):
    country_code: str
    tidal_api_client_id: str
    tidal_api_scopes: str
    tidal_api_redirect_address: str
    tidal_api_redirect_port: int
    tidekeeper_path: str
    data_path: str

    @computed_field
    @property
    def tidal_api_tokens_path(self) -> str:
        return self.data_path + "/tidal_api_tokens.json"

    @computed_field
    @property
    def music_path(self) -> str:
        return self.data_path + "/Music/Music"

    @computed_field
    @property
    def music_videos_path(self) -> str:
        return self.data_path + "/Music/Video"

    @computed_field
    @property
    def cache_path(self) -> str:
        return self.data_path + "/Cache"

    @computed_field
    @property
    def tidekeeper_config_path(self) -> str:
        return self.data_path + "/Tidekeeper"

    @computed_field
    @property
    def tidekeeper_music_path(self) -> str:
        return self.data_path + "/Music"

    @computed_field
    @property
    def database_path(self) -> str:
        return self.data_path + "/Database/database.db"


    model_config = SettingsConfigDict(env_prefix="LIGHTHOUSE_SERVER_", env_file=".env")

# Define logging
# Define the logging configuration

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage()
        }
        # Add exception info if available
        if record.exc_info:

            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "()": JsonFormatter
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "rotating_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": Settings().data_path + "/lighthouse_server.log",
            "level": "INFO",
            "formatter": "json",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "app": {"handlers": ["console", "rotating_file"], "level": "DEBUG", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "DEBUG"},
}
logging.config.dictConfig(log_config)
logger = logging.getLogger("app")
