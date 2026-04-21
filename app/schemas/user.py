from pydantic import BaseModel, EmailStr

# Hem kayıt olurken hem de cevap dönerken ortak olan alan
class UserBase(BaseModel):
    email: EmailStr
    username: str  # YENİ: Kayıt olurken ve veri dönerken kullanıcı adını da istiyoruz

# Kullanıcı kayıt olurken bize göndereceği veri
class UserCreate(UserBase):
    password: str

# Bizim dışarıya döneceğimiz veri formatı
class UserResponse(UserBase):
    id: int
    is_active: bool
    total_score: int  # YENİ: Oyuncu profilini çektiğinde toplam puanını da görebilsin

    class Config:
        from_attributes = True