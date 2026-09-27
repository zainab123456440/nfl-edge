from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our games router
from routes.games import router as games_router

app = FastAPI(title="NFL Edge AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect the games route to the main app
app.include_router(games_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok", 
        "message": "NFL Edge AI API is live.",
        "data_mode": "demo"
    }