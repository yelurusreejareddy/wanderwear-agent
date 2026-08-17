# Phase 10: packages this project so it runs identically anywhere,
# not just "on my machine". Real base image, real Python version,
# matched to what's actually installed and tested locally (3.12).
FROM python:3.12-slim

# Where the app actually lives inside the real container.
WORKDIR /app

# Real dependency install first, before copying the rest of the code.
# Docker caches each real step, so if only agent code changes later,
# this real pip install step is skipped on the next build, not rerun.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The real app code. closet/, docs/, supabase/ are not needed for the
# server to actually run, only agent/ is, so only that gets copied in.
COPY agent/ ./agent/

# Real secrets (.env) are never baked into the image, same reason
# .gitignore already keeps them out of git: anyone with the image
# would have them otherwise. Render's own environment variable
# settings inject these as real environment variables at runtime
# instead, load_dotenv() in our code already just no-ops if no real
# .env file exists, os.getenv() still finds them fine either way.

WORKDIR /app/agent

# Render (and most real hosts) assign a real port at runtime via the
# $PORT environment variable, not a fixed number we pick ourselves.
# Real fix for a real warning Docker gave on the first build: plain
# shell-form CMD (no brackets) lets $PORT expand correctly, but Docker
# can't then forward OS signals (like a real shutdown request) straight
# to uvicorn, only to the shell wrapping it. Writing it as JSON array
# form that explicitly calls "sh -c" gets both real things at once,
# $PORT still expands, and Docker's recommended signal-safe form.
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port $PORT"]
