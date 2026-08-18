"""
conftest.py -- pytest automatically runs this before any test file, a
real, special filename it looks for, not something we import ourselves.

Real problem this solves: importing api.py pulls in loop.py, which
builds a real OpenAI client at import time using LLM_API_KEY. Checked
directly, that real client raises immediately if the key is missing,
not just when you actually call it. In CI there is no real .env file,
so importing api.py would crash before a single test even runs.

Our real tests never call the actual Groq or Supabase APIs (that would
cost real tokens and be flaky in CI), they only check request
validation and endpoints that need no external call. So a fake,
made-up value here is honest: it only has to be a non-empty string,
nothing here ever depends on it being a real, working key.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

os.environ.setdefault("LLM_API_KEY", "test-key-not-real")
os.environ.setdefault("LLM_BASE_URL", "https://api.groq.com/openai/v1")
os.environ.setdefault("LLM_MODEL", "openai/gpt-oss-120b")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-publishable-key-not-real")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key-not-real")
