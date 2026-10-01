from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import FRONTEND_ORIGIN
from routes import auth, cron, games, props, user_props
from routes.lineups import router as lineups_router

app = FastAPI(title="NFL Odds API")

# Lets the Next.js frontend call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cron.router)
app.include_router(games.router)
app.include_router(props.router)
app.include_router(user_props.router)
app.include_router(lineups_router)

@app.get("/health")
def health():
    return {"status": "ok"}