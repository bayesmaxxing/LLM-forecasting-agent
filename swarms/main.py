from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from forecast_swarm import ForecastSwarm 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            swarm = ForecastSwarm()
            swarm_response = swarm.run(data)

            await websocket.send_text(swarm_response["content"])
    except WebSocketDisconnect:
        print("WebSocket disconnected")

