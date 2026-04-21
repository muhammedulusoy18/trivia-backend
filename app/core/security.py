from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
from app.core.config import settings

# Şifreleri hashlemek için bcrypt algoritması
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    # Kullanıcının girdiği düz şifre ile veritabanındaki şifrelenmiş metni karşılaştırma
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    # Düz şifreyi (örn: 123456) alıp anlamsız, geri döndürülemez bir metne çevirme
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()
    # Şu anki zamana göre "Son Kullanma Tarihi (exp)" oluşturma
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # Token'ı SECRET_KEY ile mühürleyip üretiyoruz
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    # Şu anki zamana, .env dosyasındaki 7 günü ekliyoruz
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt