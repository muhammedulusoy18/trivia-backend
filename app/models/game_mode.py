from sqlalchemy import Column, Integer, String
from app.db.database import Base

class GameMode(Base):
    __tablename__ = "game_modes"
    id=Column(Integer, primary_key=True,index=True)
    key=Column(String,unique=True,index=True)
    label=Column(String)
    max_question=Column(Integer)
    question_duration=Column(Integer)
