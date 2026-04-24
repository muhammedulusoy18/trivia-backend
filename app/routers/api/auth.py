from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # YENİ ASENKRON SESSION
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from sqlalchemy.future import select

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.token import Token, TokenData
from app.crud import user as user_crud
from app.core import security

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# KAYIT OLMA
@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Bu emaille daha önce kayıt olunmuş mu
    db_user = await user_crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Bu e-posta adresi zaten kullanımda."
        )
    # Yoksa, yeni kullanıcıyı oluştur
    return await user_crud.create_user(db=db, user=user_in)


# GİRİŞ YAPMA
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # NOT: OAuth2 standartlarında email alanı 'username' olarak gelir.
    user = await user_crud.get_user_by_email(db, email=form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Hatalı e-posta veya şifre.")

    # Şifreyi doğrula
    if not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Hatalı e-posta veya şifre.")

    # Giriş başarılıysa Token'ları üret
    access_token = security.create_access_token(data={"sub": user.email})
    refresh_token = security.create_refresh_token(data={"sub": user.email})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# REFRESH TOKEN
@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        # gelen refresh tokeni açıyoruz
        payload = jwt.decode(refresh_token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Geçersiz refresh token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Refresh token süresi dolmuş veya geçersiz")

    user = await user_crud.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

    new_access_token = security.create_access_token(data={"sub": user.email})
    new_refresh_token = security.create_refresh_token(data={"sub": user.email})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


def get_current_user_token(token: str = Depends(oauth2_scheme)):
    return token


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Geçersiz token: Email bulunamadı")
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Geçersiz veya süresi dolmuş token")

    user = await user_crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    return user

@router.get("/top-scores")
async def get_top_score(db:AsyncSession=Depends(get_db)):
    result=await db.execute(select(User).order_by(User.total_score.desc()).limit(10))
    top_users = result.scalars().all()
    return[
        {"username": u.username, "total_score": u.total_score}
        for u in top_users
    ]

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user