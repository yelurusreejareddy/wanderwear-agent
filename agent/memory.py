"""
memory.py -- phase 5: saving and reading real memory from Supabase.
Every question and answer the agent gives gets saved here, so a future run
can look back at what happened before instead of starting from zero.
"""
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Same pattern as loop.py's Groq client: one object that knows where the
# database is (SUPABASE_URL) and who's asking (SUPABASE_KEY), built once
# and reused for every save or read.
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def save_trip(question, answer):
    """Save one real question and its real answer into the trips table."""
    supabase.table("trips").insert({
        "question": question,
        "answer": answer,
    }).execute()


def get_recent_trips(limit=5):
    """Read back the most recently saved trips, newest first."""
    response = (
        supabase.table("trips")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


if __name__ == "__main__":
    save_trip("test question, from memory.py", "test answer, from memory.py")
    print(get_recent_trips())
