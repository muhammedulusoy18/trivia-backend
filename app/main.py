import random
import asyncio
from fastapi import WebSocket, FastAPI, WebSocketDisconnect
from contextlib import asynccontextmanager
from sqlalchemy.future import select
from sqlalchemy.sql.expression import func
from db.database import Base, engine, AsyncSessionLocal
from app.models.question import Question as question
from fastapi.middleware.cors import CORSMiddleware
from app.websockets.manager import manager
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
async def seed_questions():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(question))
        first_question = result.scalars().first()
        if not first_question:
            sorular = [
                question(question="FastAPI hangi asenkron sunucu mimarisi üzerine kurulmuştur?", option_a="Flask",
                         option_b="Starlette", option_c="Django", option_d="Tornado", correct_option="B"),
                question(question="Python'da değiştirilemez (immutable) veri tipi hangisidir?", option_a="List",
                         option_b="Dictionary", option_c="Tuple", option_d="Set", correct_option="C")
            ]
            session.add_all(sorular)
            await session.commit()
            print("Örnek sorular eklendi!")


async def get_and_send_new_question(manager_instance):
    """Yeni bir soru çeker, karıştırır ve tüm oyunculara yayınlar."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(question).order_by(func.random()).limit(1))
        db_question = result.scalars().first()

    if db_question:
        option_list = [
            {"text": db_question.option_a},
            {"text": db_question.option_b},
            {"text": db_question.option_c},
            {"text": db_question.option_d}
        ]

        # Doğru metni bul (getattr kullanımı)
        correct_text = getattr(db_question, f"option_{db_question.correct_option.lower()}")

        # Şıkları karıştır
        random.shuffle(option_list)

        shuffled_options = {}
        new_labels = ["A", "B", "C", "D"]

        for i in range(4):
            label = new_labels[i]
            text = option_list[i]["text"]
            shuffled_options[label] = text
            if text == correct_text:
                # Manager'daki doğru cevabı bu elin yeni harfiyle güncelle
                manager_instance.current_correct_answer = label

        question_packet = {
            "action": "new_question",
            "question": db_question.question,  # Modelinde sütun adı 'question'
            "options": shuffled_options
        }
        await manager_instance.broadcast(question_packet)
    else:
        print("Veritabanında soru bulunamadı.")


# --- APP AYARLARI ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Veritabanı başlatılıyor...")
    await init_db()
    await seed_questions()
    yield


app = FastAPI(title="Trivia Game Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    manager.scores[client_id] = 0

    try:
        while True:
            data = await websocket.receive_json()
            data["client_id"] = client_id
            action = data.get("action")
            if action == "chat":
                await manager.broadcast(data)
            elif action == "start_game":
                await get_and_send_new_question(manager)

            elif action == "answer":
                player_answer = data.get("answer")
                manager.current_answers[client_id] = player_answer

                await manager.broadcast({
                    "action": "chat",
                    "content": f"Oyuncu {client_id} cevap verdi, diğerleri bekleniyor..."
                })


                if len(manager.current_answers) == len(manager.active_connections):
                    for p_id, ans in manager.current_answers.items():
                        if ans.upper() == manager.current_correct_answer.upper():
                            manager.scores[p_id] += 10
                            await manager.broadcast({"action": "chat", "content": f"Oyuncu {p_id} doğru bildi! ✅"})
                        else:
                            await manager.broadcast(
                                {"action": "chat", "content": f"Oyuncu {p_id} yanlış cevap verdi! ❌"})


                    await manager.broadcast({"action": "scoreboard", "scores": manager.scores})


                    manager.current_answers = {}


                    await asyncio.sleep(3)
                    await manager.broadcast({"action": "chat", "content": "Yeni soru geliyor..."})
                    await asyncio.sleep(1)
                    await get_and_send_new_question(manager)

            else:
                print(f"Bilinmeyen eylem: {action}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({
            "action": "disconnect",
            "client_id": client_id,
            "content": f"Oyuncu {client_id} ayrıldı."
        })