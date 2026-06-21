from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://minibench:minibench@localhost:5438/minibench"
    database_url_sync: str = "postgresql+psycopg2://minibench:minibench@localhost:5438/minibench"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "*"]


settings = Settings()
