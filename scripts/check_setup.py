"""Phase 0 smoke test.

Confirms three things before we write any agent code:
  1. The .env file exists and the key loaded.
  2. We can reach the LLM provider.
  3. The model supports tool calling, which is the one feature the whole
     project depends on.

Run it with:  .venv/bin/python scripts/check_setup.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
model = os.getenv("LLM_MODEL")

if not api_key or api_key == "paste_your_key_here":
    sys.exit("No API key found. Copy .env.example to .env and paste your key in.")

client = OpenAI(api_key=api_key, base_url=base_url)

print(f"Model: {model}")
print(f"Endpoint: {base_url}\n")

# Test 1: plain chat. Proves the connection and the key work.
chat = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Reply with exactly: connection ok"}],
    max_tokens=20,
)
print("Test 1 (plain chat):", chat.choices[0].message.content.strip())

# Test 2: tool calling. This is the important one.
#
# A "tool" is just a JSON description of a function you are willing to run.
# You send that description along with the question. The model does NOT run
# anything. It replies saying "I would like you to call get_weather with
# city=Chicago". Your code is what actually runs the function and sends the
# result back. That request-and-return cycle is the entire basis of agents.
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current temperature for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                },
                "required": ["city"],
            },
        },
    }
]

reply = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "What is the temperature in Chicago?"}],
    tools=tools,
).choices[0].message

if reply.tool_calls:
    call = reply.tool_calls[0]
    print(f"Test 2 (tool calling): model asked to call "
          f"{call.function.name} with {call.function.arguments}")
    print("\nSetup is good. Tool calling works, so we can build the agent.")
else:
    print("Test 2 (tool calling): FAILED, the model answered in text instead "
          "of requesting the tool.")
    print(f"It said: {reply.content}")
    print("\nThis model cannot do tool calling. Pick a different LLM_MODEL.")
