from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Model Storage"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    cors_allow_origins: list[str] = ["http://localhost:3000"]

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "file-storage"
    db_ssl_mode: str = "disable"

    storage_dir: str = "./files"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FILE_STORAGE_")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_ssl_mode}"
        )


settings = Settings()
