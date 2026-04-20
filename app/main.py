import random
import asyncio
import time
import os
from fastapi.responses import HTMLResponse
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
async def start_timer(seconds:int,manager):

   try:
        i=0
        while i <seconds:
            await asyncio.sleep(1)
            remaining_seconds = seconds - i
            if remaining_seconds%5==0 or remaining_seconds<=5:
                await manager.broadcast({"action": "chat", "content": f"{remaining_seconds} saniye kaldı"})
            i+=1
        await manager.broadcast({"action":"chat","content":f"Süre bitti"})
        await finish_round(manager,time_is_up=True)
   except asyncio.CancelledError:
           pass

async def get_and_send_new_question(manager_instance):

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


        correct_text = getattr(db_question, f"option_{db_question.correct_option.lower()}")
        difficulty=db_question.difficulty
        if difficulty =='Kolay':
           manager.current_question_points=5
        elif difficulty =='Orta':
            manager.current_question_points=10
        elif difficulty =='Zor':
            manager.current_question_points=20

        random.shuffle(option_list)

        shuffled_options = {}
        new_labels = ["A", "B", "C", "D"]

        for i in range(4):
            label = new_labels[i]
            text = option_list[i]["text"]
            shuffled_options[label] = text
            if text == correct_text:

                manager_instance.current_correct_answer = label

        question_packet = {
            "action": "new_question",
            "question": db_question.question,
            "options": shuffled_options
        }
        await manager_instance.broadcast(question_packet)
        manager_instance.question_start_time=time.time()
        manager.timer_task = asyncio.create_task(start_timer(15, manager))
    else:
        print("Veritabanında soru bulunamadı.")



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
async def finish_round(manager,time_is_up=False):
    if time_is_up==False and manager.timer_task and not manager.timer_task.done():
        manager.timer_task.cancel()
    for p_id, ans in manager.current_answers.items():
        if ans.upper() == manager.current_correct_answer.upper():
            time_taken=manager.answer_times[p_id]-manager.question_start_time
            remaining_seconds=max(0,15-time_taken)
            bonus_points=int(remaining_seconds)
            total_earned=manager.current_question_points+bonus_points
            manager.scores[p_id] +=total_earned
            await manager.broadcast({"action": "chat", "content": f"Oyuncu {p_id} doğru bildi! ✅ (+{total_earned} Puan ⚡"} )
        else:
            await manager.broadcast(
                {"action": "chat", "content": f"Oyuncu {p_id} yanlış cevap verdi! ❌"})

    await manager.broadcast({"action": "scoreboard", "scores": manager.scores})

    manager.current_answers = {}
    manager.answer_times = {}

    await asyncio.sleep(3)
    await manager.broadcast({"action": "chat", "content": "Yeni soru geliyor..."})
    await asyncio.sleep(1)
    await get_and_send_new_question(manager)



@app.get("/")
async def get_test_page():
    html_path = "test_client.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    return {"error": "test_client.html bulunamadı!"}
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id):
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
                if not manager.is_active:
                    manager.is_active = True
                    await get_and_send_new_question(manager)
                else :
                    await websocket.send_json({"action":"chat",
                    "content": "⚠️ Oyun zaten devam ediyor!"
                    })
            elif action == "answer":
                player_answer = data.get("answer")
                manager.current_answers[client_id] = player_answer
                manager.answer_times[client_id] = time.time()

                await manager.broadcast({
                    "action": "chat",
                    "content": f"Oyuncu {client_id} cevap verdi, diğerleri bekleniyor..."
                })
                if len(manager.current_answers) == len(manager.active_connections):

                    await finish_round(manager)
            else:
                print(f"Bilinmeyen eylem: {action}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({
            "action": "disconnect",
            "client_id": client_id,
            "content": f"Oyuncu {client_id} ayrıldı."
        })