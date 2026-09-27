import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATA_MODE = os.getenv("DATA_MODE", "demo")
    THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
    BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

settings = Settings()