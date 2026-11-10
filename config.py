from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    BOT_OWNER_ID: int
    LOG_LEVEL: str = "INFO"
    WEB_APP_URL: str = ""
    SETUP_TOKEN_SECRET: str = "change-this-secret-in-railway"
    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 8080

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
