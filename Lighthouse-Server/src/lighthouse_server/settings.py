import os
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
