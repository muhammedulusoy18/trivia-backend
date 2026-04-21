from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.user import UserCreate
from app.core import security
# Şifre hashleme fonksiyonunun burada olduğunu varsayıyorum


async def get_user_by_email(db: AsyncSession, email: str):
    # Asenkron arama sorgusu
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate):
    # Şifreyi güvenli hale getir
    hashed_password = security.get_password_hash(user.password)

    # Yeni kullanıcı objesini oluştur (Modeline username eklediğimiz için buraya da ekledik)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        total_score=0  # Yeni eklediğimiz kasa
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user
async def update_user_score(db: AsyncSession ,username:str,earned_points:int):
    result=await db.execute(select(User).filter(User.username == username))
    user=result.scalar_one_or_none()
    if user:
        user.total_score+=earned_points
        await db.commit()
        await db.refresh(user)
    return user