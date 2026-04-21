import os
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri sisteme yükler
load_dotenv()

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "yedek_gizli_anahtar")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./auth_app.db")

settings = Settings()