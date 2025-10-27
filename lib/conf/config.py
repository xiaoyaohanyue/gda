from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    log_path: str = "logs/"
    session_path: str
    download_root_path: str
    github_token: str
    telegram_bot_token: str
    admin_telegram_id: int
    telegram_api_id: str
    telegram_api_hash: str
    db_url: str
    yaml_file: str = "config/config.yaml"
    model_config = ConfigDict(env_file="config/.env")

settings = Settings()
