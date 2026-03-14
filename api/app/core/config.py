
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default='TrailOne GPX API')
    app_version: str = Field(default='1.0.0')
    debug: bool = Field(default=False)
    log_level: str = Field(default='INFO')
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024)
    max_points: int = Field(default=200_000)
    temp_output_dir: str = Field(default='/tmp')

    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='TRAILONE_',
        case_sensitive=False,
        extra='ignore',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
