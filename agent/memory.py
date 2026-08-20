"""
memory.py -- phase 5: saving and reading real memory from Supabase.
Every question and answer the agent gives gets saved here, so a future run
can look back at what happened before instead of starting from zero.

Phase 12 update: trips is now real, per-user data (see migration 0010),
RLS only lets a real, logged-in user see or write their own real rows.
get_client() (auth_context.py) hands back whichever real identity is
actually asking right now, an HTTP request's real logged-in user, or a
real CLI login, this file never has to know or care which.
"""
from auth_context import get_client, get_user_id


def save_trip(question, answer):
    """Save one real question and its real answer into the trips table,
    tagged with whichever real user is asking right now."""
    get_client().table("trips").insert({
        "question": question,
        "answer": answer,
        "user_id": get_user_id(),
    }).execute()


def get_recent_trips(limit=5):
    """Read back the most recently saved trips, newest first, RLS
    already limits this to the real, current user's own rows."""
    response = (
        get_client()
        .table("trips")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


if __name__ == "__main__":
    save_trip("test question, from memory.py", "test answer, from memory.py")
    print(get_recent_trips())
