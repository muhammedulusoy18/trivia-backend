from pydantic import BaseModel

class GameModeCreate(BaseModel):
    key: str
    label: str
    max_question: int
    question_duration: int


class GameModeRead(GameModeCreate):
    id: int

    class Config:
        from_attributes = True