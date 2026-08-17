# Personal Agent

A personal multi-agent system: one orchestrator agent that routes questions to
specialist sub-agents (starting with trip planning, more added over time).
Built from scratch as a learning project, one phase at a time, with every
concept documented as we go.

**Start here: [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)** — one file,
in sections: glossary, what is an agent, what is a framework, architecture,
phase plan, status, cloud and costs, troubleshooting.

## Why this project

Most portfolio agent projects are a single chatbot. This one is a real
multi-agent system: an orchestrator that routes to specialists, specialists
that call real free APIs and hand off to each other, a memory layer, safety
limits, and a deployed service. That combination, routing, tool calling,
agent-to-agent handoff, evaluation, and deployment, maps directly onto what
2026 AI/ML engineering interviews actually test.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then paste your API key into .env
.venv/bin/python scripts/check_setup.py
```

The default provider is Groq's free tier, which is fast enough that a multi-step
agent loop stays interactive. The client is the OpenAI SDK pointed at a custom
base URL, so switching providers is a change to `.env` and nothing else.
