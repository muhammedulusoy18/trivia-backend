from pydantic import BaseModel

# Kullanıcı başarılı giriş yaptığında ona vereceğimiz JSON
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

# Sistemin, gelen Token'ı çözdüğünde içinden çıkaracağı veri
class TokenData(BaseModel):
    email: str | None = None
    username: str | None = None