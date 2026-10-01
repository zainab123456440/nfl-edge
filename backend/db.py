"""Supabase client (service-role key: server only, bypasses RLS)."""
import os
from functools import lru_cache
from supabase import Client, create_client
from dotenv import load_dotenv

# Force load the .env file so the variables are available in os.environ
load_dotenv()

# Read directly from the environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

@lru_cache
def get_db() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        # Better error handling to tell you exactly which one is missing
        url_status = "Found" if SUPABASE_URL else "Missing"
        key_status = "Found" if SUPABASE_SERVICE_ROLE_KEY else "Missing"
        
        raise RuntimeError(
            f"Supabase credentials failed to load from .env file.\n"
            f"SUPABASE_URL: {url_status}\n"
            f"SUPABASE_SERVICE_ROLE_KEY: {key_status}\n"
            "Please ensure your .env file is in the root directory and contains both keys."
        )
        
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)