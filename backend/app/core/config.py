from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pallet Manager API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 30

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_exports: str = "pallet-exports"
    minio_bucket_imports: str = "simulator-imports"
    minio_secure: bool = False


settings = Settings()
