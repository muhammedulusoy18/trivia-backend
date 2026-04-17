from fastapi import WebSocket
from typing import List
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.scores:dict = {}
        self.current_answers:dict = {}
    #async tanımladık diğer işlemleri bloklamasın diye
    async def connect(self ,websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self,websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self,message:dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except RuntimeError:
                dead_connections.append(connection)
        for dead in dead_connections:
            if dead in self.active_connections:
                self.active_connections.remove(dead)
manager=ConnectionManager()



