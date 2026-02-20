from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8080
    log_file: str = "/var/log/client.log"
    random_seed: int | None = None
    timeout: float = 5.0


def get_settings():
    return Settings()
