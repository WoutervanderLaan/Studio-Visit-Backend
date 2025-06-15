from pydantic_settings import BaseSettings, SettingsConfigDict, DotEnvSettingsSource
from pydantic import Field, ValidationError
from functools import lru_cache
from pathlib import Path
from passlib.context import CryptContext
import os
from dotenv import dotenv_values


class BaseConfig(BaseSettings):
    # env
    environment: str = Field(default="development")
    secret_key: str = Field(default="")
    refresh_secret_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    openai_org_id: str = Field(default="")

    # constants
    uploads_dir: str = Field(default="uploads")
    pwd_context: CryptContext = Field(
        default=CryptContext(schemes=["bcrypt"], deprecated="auto")
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        base_env_path = Path(".env")
        base_env_vars = dotenv_values(base_env_path) if base_env_path.exists() else {}
        environment = os.getenv("ENVIRONMENT") or base_env_vars.get(
            "ENVIRONMENT", "development"
        )

        env_specific_path = Path(f".env.{environment}")

        return (
            init_settings,
            env_settings,
            DotEnvSettingsSource(settings_cls, env_specific_path),
            DotEnvSettingsSource(settings_cls, base_env_path),
            file_secret_settings,
        )


@lru_cache()
def get_settings() -> BaseConfig:
    try:
        return BaseConfig()
    except ValidationError as e:
        print("❌ Environment configuration error:")
        print(e.json())
        raise SystemExit("Missing or invalid environment variables. Exiting.")
