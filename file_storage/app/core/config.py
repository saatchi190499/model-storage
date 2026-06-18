from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Model Storage"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    cors_allow_origins: list[str] = ["http://localhost:3000"]
    enable_ui: bool = False
    enable_api_docs: bool = False

    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "file-storage"
    db_ssl_mode: str = "disable"

    storage_dir: str = "./files"
    api_key: str = ""
    previous_api_key: str = ""
    max_upload_bytes: int = 250 * 1024 * 1024
    max_zip_files: int = 5000
    max_zip_uncompressed_bytes: int = 2 * 1024 * 1024 * 1024
    max_zip_compression_ratio: int = 100
    stream_chunk_bytes: int = 1024 * 1024
    accel_redirect_enabled: bool = False
    accel_redirect_prefix: str = "/internal-model-storage/"
    json_logs: bool = True
    log_dir: str = "./logs"
    log_level: str = "INFO"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FILE_STORAGE_")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_ssl_mode}"
        )

    @property
    def accepted_api_keys(self) -> tuple[str, ...]:
        active = self.api_key.strip()
        if not active:
            return ()

        previous = self.previous_api_key.strip()
        if previous and previous != active:
            return active, previous
        return (active,)


settings = Settings()
