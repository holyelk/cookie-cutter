from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "backend-service"
    environment: str = "dev"
    log_level: str = "INFO"
    
    # Telemetry
    otlp_grpc_endpoint: str = "http://localhost:4317"
    enable_telemetry: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
