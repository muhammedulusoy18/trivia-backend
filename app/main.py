import random
import asyncio
from fastapi import WebSocket,FastAPI,WebSocketDisconnect
from contextlib import asynccontextmanager
from sqlalchemy.future import select
from sqlalchemy.sql.expression import func
from db.database import Base,engine,AsyncSessionLocal
from app.models.question import Question as question
from fastapi.middleware.cors import CORSMiddleware
from app.websockets.manager import manager
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
async def seed_questions():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(question))
        first_question=result.scalars().first()
        if  not first_question:
            sorular=[
                question(question="FastAPI hangi asenkron sunucu mimarisi üzerine kurulmuştur?", option_a="Flask",
                         option_b="Starlette", option_c="Django", option_d="Tornado", correct_option="B"),
                question(question="Python'da değiştirilemez (immutable) veri tipi hangisidir?", option_a="List",
                         option_b="Dictionary", option_c="Tuple", option_d="Set", correct_option="C")

            ]
            session.add_all(sorular)
            await session.commit()
            print("örnek sorular eklendi!")
@asynccontextmanager
async def lifespan(app:FastAPI):
    print("veritabanı başlatılıyor...")
    await init_db()
    await seed_questions()
    yield

app = FastAPI(title="Trivia Game Server",
              lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket:WebSocket,client_id:int):
    await manager.connect(websocket)
    manager.scores[client_id]=0


    try:
        while True:
            data= await websocket.receive_json()
            data["client_id"]=client_id
            action=data.get("action")
            if action=="chat":
                await manager.broadcast(data)
            elif action=="start_game":
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(question).order_by(func.random()).limit(1))
                    db_question=result.scalars().first()
                if db_question:
                    option_list=[
                        {"key": "A", "text": db_question.option_a},
                        {"key": "B", "text": db_question.option_b},
                        {"key": "C", "text": db_question.option_c},
                        {"key": "D", "text": db_question.option_d}
                                 ]
                    correct_text=getattr(db_question,f"option_{db_question.correct_option.lower()}")
                    manager.current_correct_answers_text=correct_text
                    random.shuffle(option_list)
                    shuffled_options={}
                    new_labels = ["A", "B", "C", "D"]
                    for i in range(4):
                        shuffled_options[new_labels[i]] = option_list[i]["text"]
                        if option_list[i]["text"] == correct_text:
                            manager.current_correct_answers=new_labels[i]

                    questions={
                        "action":"new_question",
                        "question":db_question.question,
                        "options":{
                            "a":db_question.option_a,
                            "b":db_question.option_b,
                            "c":db_question.option_c,
                            "d":db_question.option_d
                    }
                    }
                    await manager.broadcast(questions)
                else:
                    print("veritabanında soru yok")


            elif action=="answer":
                player_answer = data.get("answer")
                manager.current_answers[client_id]=player_answer
                await manager.broadcast({"action":"chat" ,
                                         "content":f"oyuncu {client_id} cevap verdi diğer oyuncular bekleniyor"})
                if len(manager.current_answers)==len(manager.active_connections):
                    for p_id,ans in manager.current_answers.items():
                        if ans.upper()==manager.current_correct_answers.upper():
                            manager.scores[p_id]+=10
                            await manager.broadcast({"action":"chat",
                                                     "content":f"oyuncu {p_id} doğru cevap verdi"
                                                     })

                        else:
                            await manager.broadcast({"action":"chat",
                                                     "content":f"oyuncu {p_id} yanlış cevap verdi"
                                                    })

                    await manager.broadcast({"action": "scoreboard",
                                     "scores": manager.scores
                                     })
                    manager.current_answers = {}
                    await asyncio.sleep(3)  # 3 saniye bekleme süresi
                    await manager.broadcast({"action": "chat", "content": "Yeni soru geliyor..."})
                    await asyncio.sleep(1)

            else:
                print(f"bilinmeyen eylem: {action}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        disconnect_message={"action":"disconnect","client_id":client_id}
        await manager.broadcast(disconnect_message)




