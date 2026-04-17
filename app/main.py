from fastapi import WebSocket,FastAPI,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.websockets.manager import manager
app = FastAPI()
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
            data=await websocket.receive_json()
            data["client_id"]=client_id
            action=data.get("action")
            if action=="chat":
                await manager.broadcast(data)
            elif action=="start_game":
                soru_paketi = {
                    "action": "new_question",
                    "question": "FastAPI hangi asenkron sunucu mimarisi üzerine kurulmuştur?",
                    "options": {
                        "A": "Flask",
                        "B": "Starlette",
                        "C": "Django",
                        "D": "Tornado"
                    }
                }
                await manager.broadcast(soru_paketi)
            elif action=="answer":
                player_answer = data.get("answer")
                manager.current_answers[client_id]=player_answer
                await manager.broadcast({"action":"chat" ,"content":f"{client_id} cevap verdi diğer oyuncular bekleniyor"})
                if len(manager.current_answers)==len(manager.active_connections):
                    for p_id,ans in manager.current_answers.items():
                        if ans=="B" or ans=="b":
                            manager.scores[client_id]+=10
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
            else:
                print(f"bilinmeyen eylem: {action}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        disconnect_message={"action":"disconnect","client_id":client_id}
        await manager.broadcast(disconnect_message)




