from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.game_mode import GameMode

async def get_all_modes(db: AsyncSession):
    result=await db.execute(select(GameMode))
    return result.scalars().all()

async def get_mode_by_key(db: AsyncSession, key: str):
    result=await db.execute(select(GameMode).filter(GameMode.key==key))
    return result.scalar_one_or_none()

async def create_mode(db: AsyncSession, key:str,label:str,max_question:int,duration:int):
    new_mode=GameMode(key=key,label=label,max_question=max_question,duration_duration=duration)
    db.add(new_mode)
    await db.commit()
    await db.refresh(new_mode)
    return new_mode