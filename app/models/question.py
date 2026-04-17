from sqlalchemy import Column, String, Integer
from db.database import Base

class Question(Base):
    __tablename__="question"
    id = Column(Integer,primary_key=True,index=True)
    question = Column(String,index=True)
    option_a = Column(String)
    option_b = Column(String)
    option_c = Column(String)
    option_d = Column(String)
    correct_option= Column(String)