# Personal Agent, full documentation

One file, in sections, so everything is in one place to search and refer
back to. Read top to bottom the first time, then jump to a section when you
need it.

- [1. Glossary](#1-glossary)
- [2. What is an agent](#2-what-is-an-agent)
- [3. What is a framework](#3-what-is-a-framework)
- [4. Architecture, the whole system](#4-architecture-the-whole-system)
- [5. Phase plan](#5-phase-plan)
- [6. Status](#6-status)
- [7. Cloud hosting and costs](#7-cloud-hosting-and-costs)
- [8. Troubleshooting](#8-troubleshooting)
- [9. MCP (Model Context Protocol)](#9-mcp-model-context-protocol)
- [10. Reading agent/loop.py, for a total beginner](#10-reading-agentlooppy-for-a-total-beginner)

---

## 1. Glossary

Every term used in this project, plain language. Come back here whenever you
forget what something means.

**Agent.** A program that loops: think, act, observe, repeat, until it has a
real answer, then it stops. The opposite of a normal script, which just runs
top to bottom once and is done.

**Tool.** A plain Python function you wrote, described to the LLM as a JSON
object so it knows the function exists and what arguments it takes. The LLM
never runs your function itself. It only ever asks for it to be run. Your
own code is what actually runs it.

**LLM (Large Language Model).** The "thinking" part. We rent access to one
through Groq instead of training our own. It reads text and tool results,
and decides what to do next or what to answer.

**Groq.** The company whose free API we use to reach the LLM. Not an agent
by itself, just a rented brain. What makes a call "the orchestrator" or "the
travel agent" is only the instructions and tool list your code sends
alongside the question, not a separate program. See section 4.

**Orchestrator agent.** A role, not a separate program. It is Groq, called
with the instruction "read this question and decide which specialist should
handle it," and a tool list containing only "call this sub-agent" options.
Its only job is routing.

**Sub-agent (specialist agent).** Also just Groq, called with a different
instruction and a different tool list. The travel agent's instruction is
"plan a real trip using real data," and its tools are things like
`get_weather` and `find_places`.

**Framework.** Pre-built structure for a common problem, so you don't
rewrite the repetitive parts from scratch every time. You fill in your
specific logic into the structure it already provides. See section 3.

**Web server.** A program that runs continuously and waits for requests
arriving over the internet, does the work, and sends a response back. Never
stops on its own.

**API (Application Programming Interface).** A defined way for one program
to ask another program to do something and get an answer back, without
either program needing to know how the other one is built inside. Your
React frontend calls your Python backend's API.

**FastAPI.** The Python library we use to build our web server. Chosen
because everything else in this project, Groq's client, embeddings, agent
code, is also Python, so there is one language end to end instead of two.

**Frontend.** The part of the app that runs in the user's browser. Built
with React. Draws buttons, text boxes, and pages. Knows nothing about
weather data or your wardrobe by itself, it only displays what the backend
sends it.

**Backend.** The part of the app that runs on a server, out of the user's
sight. Built with Python and FastAPI. Holds the actual agent logic, calls
Groq, calls tools, talks to the database.

**React.** A JavaScript library for building the frontend. We build this
from scratch together in a later phase, explained line by line.

**PWA (Progressive Web App).** A website that can be "installed" onto a
phone's home screen from the browser, gets its own icon, opens full screen
with no browser bar visible, and can work partly offline. Costs nothing,
needs no app store. This is what we are building instead of a native
iPhone/Android app.

**Supabase.** A free hosted service that bundles a Postgres database, file
storage, and a login system together. This is the agent's memory. Without
it, the agent forgets everything the moment a conversation ends.

**Render.** The company that hosts our Python backend, meaning it runs a
computer for us all day every day so the server is always reachable on the
internet. Chosen over AWS because Render's free tier needs no credit card
and cannot silently charge you. See section 7.

**Docker.** A way to package your code, plus everything it needs to run
(the exact Python version, the exact libraries), into one bundle that runs
identically on any computer. Used in a later phase so "it works on my
machine" stops being a problem.

**CI/CD (Continuous Integration, Continuous Deployment).** Automation that
tests your code every time you save a change, and if the tests pass,
automatically publishes the new version. We use GitHub Actions for this,
free, in a later phase.

**LangGraph.** A framework that automates the bookkeeping of the agent
loop: carrying the conversation state between steps, looping until done,
handing off between agents. See section 3 for exactly what it does and does
not automate.

**RAG (Retrieval-Augmented Generation).** Instead of asking the LLM to
answer from memory, you first retrieve real data relevant to the question
(your wardrobe, your past trips, real places nearby), and hand that data to
the LLM so it answers using facts instead of guessing.

**Embedding.** A way of turning text into a list of numbers that captures
its meaning, so "sunny weather" and "clear skies" end up as similar number
lists even though the words are different. Used for search over your own
saved data.

**MCP (Model Context Protocol).** A standard, shared shape for describing a
tool, so any AI agent that speaks MCP can use it, not just the one program
it was originally written for. Like USB-C: one plug shape, works across
devices, instead of a different cable for every brand. See section 9.

**Vision model / multimodal model.** A model that can take a real image as
input, not just text, and reason about what is actually in it. `qwen/qwen3.6-27b`
is the one free vision-capable model on Groq. Used in phase 7 to draft a
real label, category/color/style, from a real photo of a real clothing
item.

**Migration.** A plain `.sql` file, saved in the project itself and tracked
the same way as the Python code, that records one real change made to the
database's structure. The real, permanent record of "what changed and why,"
instead of relying on a dashboard's own history, which can be overwritten or
lost. Ours live in `supabase/migrations/`.

**Guardrail.** A deterministic, code-level check that catches a model's
mistake at a specific point, before it, during it, or after it, rather than
trusting the model to behave correctly on its own. Never another LLM call,
that would just move the unreliability somewhere else instead of removing
it. Real examples already built in this project: `today`'s real date
(catches a bad input before the model ever sees it), `TOKEN_BUDGET` and the
step cap (catches a runaway action), `find_failed_tool_calls` and
`has_geocoded_yet` (catch the model about to act on a mistake),
`extract_real_place_names` (catches a wrong claim before it reaches the
final answer).

---

## 2. What is an agent

A normal script runs top to bottom, once, and stops. An agent is different
because it loops.

**The loop:**

```
    THINK
      |
      v
    ACT  ---->  OBSERVE
      ^            |
      |            |
      +------------+
   (loop again, or answer and stop)
```

1. **Think.** The LLM (Groq) reads the question and the list of tools your
   code is offering. It decides what to do next.
2. **Act.** Your own Python code runs the tool the LLM picked. The LLM never
   runs anything itself, it only ever asks for a tool to be run.
3. **Observe.** The result of that tool goes back to the LLM, along with the
   whole conversation so far. The LLM decides: is this enough to answer, or
   do I need to think again and use another tool.

That repeats until the LLM has enough real information to answer, then it
stops and replies in plain text instead of asking for another tool.

A plain chatbot does step 1 and stops there, it never acts or observes.
That is the entire difference between "chatbot" and "agent."

**Worked example: "hows the weather today"**

1. Your code sends the question, plus your tool list (for example
   `get_weather`), to Groq together in one request.
2. Groq reads it and replies: "please call get_weather with city=Chicago."
   It does not know the temperature yet, it only picked the tool.
3. Your code actually runs `get_weather("Chicago")`, a real Python function
   that calls a weather website and gets real numbers back.
4. Your code sends that result back to Groq, along with the conversation so
   far.
5. Groq reads the real temperature and decides one tool call was enough, so
   it writes the final answer and stops.

If the question needed two tools, say, first look up a city's coordinates,
then get weather for those coordinates, step 5 would instead say "call
another tool," and the loop would run again before answering.

**The tool list belongs to your code, not to Groq.** Groq has no memory
between requests. It does not "have" a fixed list of tools sitting around.
Every single time you call it, your code sends the tool list fresh, along
with the question. This is what lets the same Groq account act as ten
different agents, just by changing which tool list and which instructions
you send it. See section 4.

---

## 3. What is a framework

A framework is pre-built structure for a common problem, so you don't
rewrite the repetitive parts from scratch every time. You fill in your
specific logic into the structure it already provides.

Think of it like a printed form versus a blank page. A blank page, you
decide everything, where the name goes, how big the box is. A form already
has "Name:" and a box, "Date:" and a box, laid out for you, you just fill in
the blanks. FastAPI is a framework for web servers, it already knows how to
listen for requests and send responses, you just fill in what happens when
a specific request arrives.

**LangGraph specifically.** It is a framework for agent loops. It does not
make the decisions for you, Groq still decides "route to travel agent" or
"call this tool," exactly as in section 2. What it automates is the
bookkeeping around those decisions:

- Without it: you hand-write a `while` loop, hand-write `if` statements
  checking what Groq asked for, and manually pass the growing conversation
  history into every single call yourself.
- With it: you describe the possible steps as **nodes** (one node per
  agent, like "orchestrator" or "travel agent"), and the possible paths
  between them as **edges** (orchestrator can go to travel agent, travel
  agent can go to wardrobe agent). LangGraph carries the conversation state
  between nodes automatically, so you stop manually threading it through
  every function call by hand.

We build the loop by hand first, in phase 2, specifically so LangGraph in
phase 8 is never a black box, we already know exactly what it is automating
for us before we let it do that automation.

---

## 4. Architecture, the whole system

**Every piece, and why it exists:**

```
        You, on the website (React, in your browser)
                       |
                       v
        Render: your API server (Python, FastAPI)
                       |
                       v
              Orchestrator agent
           (Groq, reads the question,
            decides which specialist)
                /                \
               v                  v
       Travel sub-agent      More agents later
        /      |      \
       v       v        v
    Groq   Supabase   Free tools
  (thinks) (your data, (weather, places,
           saved trips)  geocoding)
```

Groq, Supabase, and the free tools are not separate steps in a fixed order.
They are things the sub-agent reaches for, one at a time, during its own
think, act, observe loop.

**What each piece is for:**

| Piece | What it is | Why we need it | Cost |
|---|---|---|---|
| React | Frontend library, runs in the browser | Draws what the user sees and clicks | Free |
| FastAPI | Python web server library | Lets the website talk to our Python agent code over the internet | Free |
| Render | Hosting, a computer that runs our server all day | A laptop cannot be a permanent server, it turns off and changes networks | Free tier, no card |
| Groq | Rents access to an LLM | The "thinking" step in every agent loop | Free tier, no card |
| Supabase | Database, file storage, and login, bundled | Agent memory, without it every conversation starts from zero | Free tier, no card |
| Open-Meteo | Free weather API | Real forecasts for the travel agent, no invented weather | Free, no signup |
| OpenStreetMap (Nominatim, Overpass) | Free maps data | Turns a city name into coordinates, finds real restaurants and attractions | Free, no signup |
| Docker | Packages code to run identically anywhere | Later phase, this is what "deployment" means concretely | Free |
| GitHub Actions | Runs tests automatically on every save | Later phase, this is what "CI/CD" means concretely | Free on public repos |

**One real question, traced step by step.**

Question: "I have 2 days in Nashville next weekend, what should I do and
what do I pack."

1. You send the question. It reaches the Render server, which hands it to
   the orchestrator.
2. Orchestrator asks Groq: which agent handles this. Groq sees travel dates
   and packing, routes to the travel agent.
3. The travel agent's own loop begins. Groq decides step by step which tool
   to call, and in what order.
4. Tool call: geocode Nashville. OpenStreetMap turns the city name into
   latitude and longitude.
5. Tool call: get the weather forecast. Open-Meteo returns real temperatures
   for those exact dates. This has to happen after step 4, because the
   weather API needs coordinates, not a city name.
6. Tool call: find real places. OpenStreetMap returns actual attractions and
   restaurants nearby, nothing invented.
7. Handoff to the wardrobe agent. The travel agent passes along the weather
   and activity types so packing can be planned.
8. Groq writes the final answer, using only the real data gathered above.
9. Supabase saves the trip, so you can come back later and say "move the
   museum to day 2," and it remembers day 1.

**Orchestrator vs Groq, the part that is easy to misread.** Groq is one
rented brain. It has no fixed identity. What makes one call "the
orchestrator" and another call "the travel agent" is only the instructions
and the tool list your code sends alongside the question at that exact
moment.

- Call 1, acting as orchestrator: instruction is "route this to the right
  specialist," tools are `call_travel_agent`, `call_stylist_agent`.
- Call 2, acting as travel agent: instruction is "plan a real trip using
  real data," tools are `geocode`, `get_weather`, `find_places`.

Same Groq underneath both. There is no separate orchestrator program
running somewhere, only a different job description handed to the same
rented brain each time.

**Website vs app, and what we are actually building:**

| | Website / web app | Native app |
|---|---|---|
| Where it runs | Any browser, phone or computer | Only after downloading from an app store |
| Updating it | Push new code, everyone gets it instantly | Users must download a new version |
| Built with | HTML, CSS, JavaScript, React | Swift (iPhone), Kotlin (Android), two separate codebases |
| Cost to publish | Free | Apple charges 99 dollars a year, Google charges 25 dollars once |
| Camera, location, notifications | Mostly available, some limits | Fully available |
| Review process | None | App stores can reject you |

We are building a Progressive Web App (PWA), meaning a website built with
React that can be installed onto a phone's home screen, opens full screen
with its own icon, and works partly offline. Same React and FastAPI skills,
costs nothing, no app store.

---

## 5. Phase plan

We add one real capability at a time. Every phase leaves you with something
that actually runs, nothing is built halfway and left broken.

| Phase | What you build | What breaks if you skip it |
|---|---|---|
| 0 | Get the two free keys (Groq, Supabase), confirm Groq responds | Nothing to build on |
| 1 | One tool by hand, no framework: geocode a city | You would not understand what a framework hides from you later |
| 2 | The full think, act, observe loop, still by hand | This loop is the entire concept of an agent, skipping it fakes the resume line |
| 3 | Add a dated weather tool (`daily`, with `start_date`/`end_date`) and places tools, chain them in the right order | Teaches sequencing: weather needs coordinates first. Note: our phase 1 practice tool used `current`, which only ever means right now and cannot answer "next weekend," a real forecast needs explicit dates instead |
| 4 | Self correction: what happens when a tool call fails or returns nothing | Real APIs fail constantly, this is what "robust" means in practice |
| 5 | Save to Supabase, so the agent remembers your trip | Without this the agent forgets everything the moment you close the tab |
| 6 | Safety limits: cap tool calls per question, cap spend | Protects your free quota from a runaway loop |
| 6.1 | Bug fixes found by a real stress test: `find_places` category to OSM key mapping (`beach` is `natural=beach`, not `amenity=beach`), stop discarding real partial results when one tool fails, handle Open-Meteo's forecast horizon (about 16 days out) honestly instead of retrying pointlessly | A real multi-day trip question exposed all three live, see phase 6 notes below |
| 6.2 | Real day-by-day itinerary structure, using arrival/departure time and the real daily `weather_code` for rain-aware suggestions per day | This is the actual difference between "one paragraph" and "plan a trip" |
| 6.3 | Real conversation memory across a trip, so "I want Mexican specifically" mid-trip knows what was already planned | Right now every question starts a brand new conversation from zero, even though phase 5 saves the result afterward |
| 7 | Wardrobe/stylist agent, real photographed wardrobe, real handoff between two agents | The multi-agent piece, rare and valuable on a resume. Scope corrected mid-build from generic packing text to a real stylist reasoning over Sreeja's actual real, photographed clothes, with a feedback loop and gap-analysis shopping suggestions, see phase 7 notes in section 6 |
| 8 | Rebuild the orchestrator in LangGraph | You already know the loop by hand, so the framework is no longer a black box |
| 9 | Wrap it in FastAPI, so a website can talk to it | Turns the script into an actual reachable service. Real, evidence-based bug found here: LangGraph's `recursion_limit` counts every node visit, not "rounds", see phase 9 notes |
| 10 | Docker, then deploy to Render | This is what "I deployed to the cloud" means, concretely |
| 11 | GitHub Actions runs your tests on every save | This is what "CI/CD" means, concretely |
| 12 | Real login with Supabase Auth, then replace `temporary_allow_all_access` with a real per-user RLS policy | Without this, `trips` stays readable and writable by anyone with the key, the temporary policy from phase 5 was never meant to be permanent |
| 13 | React frontend, built from scratch, as a PWA | The part the user actually sees and installs |

Phases 1 to 2 must come before 8, because LangGraph only makes sense once
you already know what it is automating. Phase 6 (safety limits) comes
before phase 7 (a second agent) on purpose, adding more agents without
spend caps first is how a free tier gets burned through in minutes.

---

## 6. Status

What is actually built right now, versus what is only planned. Update this
section every time a phase finishes.

**Done:**
- Project folder created at `/Users/boo/Documents/personal-agent`
- Python virtual environment set up (`.venv`)
- `requirements.txt` started with `openai` (used to talk to Groq, since Groq
  uses the same message format as OpenAI) and `python-dotenv`
- `.env.example` written, showing what keys are needed without exposing
  real ones
- `.gitignore` written, so real keys and the virtual environment never get
  committed
- `scripts/check_setup.py` written, a smoke test that confirms the Groq key
  works and that the model supports tool calling
- This documentation
- Groq account created, real key saved in `.env` (gitignored, never pushed)
- `check_setup.py` run successfully: plain chat works, and tool calling
  works, Groq correctly asked to call `get_weather` instead of guessing
- Supabase project created (`personal-agent`, region us-east-2), with
  "Automatically expose new tables" turned off and "Enable automatic RLS"
  turned on, so every new table starts private by default, deny-all until
  we write a rule. Project URL and publishable key saved in `.env`.

- `agent/geocode.py` written and tested: `geocode_city(city_name)` calls
  Nominatim for real and returns real coordinates. Tested with Nashville,
  Chicago, and a nonsense name (correctly returns `None`).
- `agent/weather.py` written and tested: `get_weather(lat, lon)` calls
  Open-Meteo's `current` weather and returns real temperature and weather
  code. Tested with Nashville and Chicago coordinates.
- Confirmed `current` only ever means right now, cannot answer a future
  dated question like "next weekend," a real forecast needs `daily` plus
  `start_date`/`end_date` instead, this is noted against phase 3 above.
- `agent/loop.py` written and tested: the real think, act, observe loop, by
  hand, no framework. Asked "what's the weather like in Nashville right
  now," and Groq correctly called `geocode_city` first, then `get_weather`
  with the coordinates that came back, then answered in plain English.
  Groq figured out that order on its own, it was never hardcoded.
- `agent/forecast.py` written and tested: `get_forecast(lat, lon,
  start_date, end_date)` uses Open-Meteo's `daily` endpoint, returns one
  clean dictionary per day. Tested with 2 days and 3 days, different cities.
- `agent/places.py` written and tested: `find_places(lat, lon, category)`
  uses OpenStreetMap's Overpass API, returns real nearby places with clean
  names, hit and recovered from two genuine transient Overpass server
  failures (a `406` from a missing `User-Agent`, and unrelated `504`/empty
  response flakiness on the free public server) along the way.
- `agent/loop.py` extended with both new tools, loop cap raised from 5 to 8
  steps. Ran a full real trip question, "I'm visiting Nashville on August
  15 and 16, 2026, what will the weather be like, and where should I eat,"
  and Groq correctly chained `geocode_city`, then `get_forecast`, then
  `find_places`, then answered using only real data.
- Hit and fixed two real Groq behavior problems along the way, worth
  remembering: (1) Groq has no built-in sense of today's date and guessed
  `2024` instead of `2026` until we added a system message giving it the
  real date from Python's own `datetime.date.today()`. (2) Groq initially
  tried to plan all three tool calls at once before it had real results,
  writing a literal placeholder string as a coordinate, which broke its own
  output format entirely (a `400 tool_use_failed` error from the API, not
  even a normal reply). Fixed by explicitly instructing it, in that same
  system message, to call one tool at a time and always wait for the real
  result first. Both fixes are prompt-level, not code-level, a real example
  of prompt engineering fixing a real reliability problem.

- Phase 4 done: the tool call inside `agent/loop.py`'s loop is now wrapped
  in `try`/`except`. Any tool failure, the `KeyError` from Open-Meteo's
  `{"error": true, ...}` response, the `JSONDecodeError` from flaky
  Overpass, a future failure we haven't even seen yet, gets caught in this
  one place and turned into `{"error": str(error)}`, sent back to Groq as a
  normal tool result instead of crashing the whole program.
- The system message was extended to tell Groq what to do when it sees an
  `"error"` field: try once more with corrected arguments if the mistake
  looks fixable, otherwise tell the user honestly instead of inventing an
  answer.
- Tested against a real failure: asked for weather on September 10, 2026,
  which is genuinely outside Open-Meteo's allowed forecast range. The agent
  tried `get_forecast` once, got the real error, tried once more with a
  slightly different range, failed again, then gave an honest, calm answer
  explaining it couldn't retrieve that forecast, no crash, no invented data.

- Phase 5 done, real memory. `supabase/migrations/0001_create_trips.sql`
  created a `trips` table (`id`, `question`, `answer`, `created_at`) plus a
  deliberately temporary, permissive RLS policy, `temporary_allow_all_access`,
  named that way on purpose since there's no login system yet to check a
  real identity against, phase 12 replaces it with a real per-user policy.
  From now on every SQL change gets its own numbered file in
  `supabase/migrations/`, that folder, tracked in git, is the real
  permanent record, not the dashboard's own query history, which can be
  silently overwritten by reusing the same query tab.
- Hit a second, separate permission error on the first real save attempt:
  `permission denied for table trips`. This is a genuinely different layer
  than RLS, table-level grants, an earlier, coarser gate that RLS is
  checked after. Traced back to unchecking "Automatically expose new
  tables" in phase 0, on purpose, new tables start with no API access at
  all until explicitly granted. Fixed with
  `supabase/migrations/0002_grant_anon_access.sql`, granting only `select`
  and `insert` to the `anon` role, nothing broader than what the code
  actually uses.
- `agent/memory.py` written: `save_trip(question, answer)` and
  `get_recent_trips(limit)`, using the official `supabase` Python client.
  `loop.py` now calls `save_trip` automatically every time it returns a
  real final answer. Tested end to end: ran the real Nashville trip
  question, confirmed the exact row persisted in Supabase by reading it
  back with `get_recent_trips`. Along the way, Overpass flaked again for
  real, and phase 4's self correction handled it live, unscripted, giving
  real weather plus an honest "couldn't find restaurants" instead of
  crashing, and that answer still saved correctly.

- Phase 6 done, real cost tracking and a real budget. Confirmed Groq's
  response includes real `usage.total_tokens` per call. `loop.py` now sums
  this across the whole question and enforces `TOKEN_BUDGET = 8000`,
  stopping early with an honest message if crossed, verified by temporarily
  lowering the budget to 1000 and watching it correctly cut off mid-question
  instead of continuing. A real full trip question cost 5,514 tokens,
  notably 2,695 of that in the single final step, because the full
  43-restaurant list got sent back to Groq to summarize, a concrete lesson
  that result size drives cost directly, worth trimming in a future pass.
- Also hit and fixed a second, separate reliability gap while testing this:
  Groq itself occasionally fails to produce a valid tool call at all (a
  `400 tool_use_failed` straight from the API), which phase 4's `try`/
  `except` never covered, since that only wraps our own tool functions, not
  the call to Groq. Added a bounded retry, up to 3 attempts, around the
  Groq call itself, since this is usually a one-off sampling issue that
  succeeds on a second try, with an honest fallback message if it doesn't.

- No real ratings or review data anywhere in the project, confirmed by
  checking rather than assuming. OpenStreetMap carries zero rating or
  review fields on any of the 43 real results checked. Yelp ended its free
  tier entirely in 2026, paid only. Foursquare's free tier explicitly
  excludes ratings, billed from the first call. This is not a gap to fix
  later, it's an industry-wide fact: review data is a paid, proprietary
  asset for every major provider, worth remembering for any future project.
- `find_places` reworked: now scores each result with `_completeness_score`
  (does it have a name, website, phone, opening hours) and returns only the
  top 10, most-documented first. Verified directly: 43 raw results in, 10
  clean results out, no internal score leaking into the returned data.
  Corrected mid-build after a sharp question, "how do you rate the place
  without knowing it": this score does NOT measure quality, it only
  measures how well-documented a listing is on OpenStreetMap, a beloved
  local place with a sparse listing can score low, a mediocre chain with a
  full profile can score high. Both the function's docstring and the
  tool's description sent to Groq were rewritten to say this plainly, and
  Groq is explicitly told never to describe these results as top-rated or
  best.
- Full end-to-end token comparison (old 43-result run was 5,514 tokens
  total, 2,695 of that in the final summarization step alone) not yet
  re-measured with the trimmed version, Overpass had a genuinely rough
  stretch, four failures in a row, right when we went to test it live. Not
  worth burning more Groq quota chasing a flaky external service having a
  bad few minutes, that's the exact waste phase 6 exists to avoid. Retry
  next session for a clean before/after number.
- No login system, so `trips` is still shared, unfiled by user, protected
  only by the temporary permissive policy
- No frontend started
- Ran a real stress test: "I'm visiting Miami, arrive Aug 20 at 1pm, leave
  Aug 24 at 4pm, plan a beautiful trip." Exposed three real, concrete bugs,
  now phase 6.1: (1) Groq asked `find_places` for `category: "beach"` and
  got zero results back, silently, because our query hardcodes
  `amenity=`, and beaches are tagged `natural=beach` in OpenStreetMap, not
  an amenity at all, same problem hits parks and viewpoints; (2) the agent
  had a real, successful `get_weather` result, 29.8°C and clear, and the
  final answer still said "I was unable to plan a trip for you," throwing
  away a real result instead of reporting it; (3) `get_forecast` failed
  because Aug 24 falls outside Open-Meteo's real forecast horizon, about
  16 days out from today, confirmed directly against the API's own error
  message, and instead of recognizing this and saying so, Groq retried the
  same doomed call twice more, wasting real tokens and two Groq API calls
  on something no retry could ever fix.
- Phase 6.1 done, all three bugs fixed and reverified against the exact
  same Miami question that first exposed them.
  (1) `places.py` now has `CATEGORY_TAGS`, mapping category names to the
  right OpenStreetMap key, `beach` to `natural`, `park` to `leisure`,
  `viewpoint`/`museum`/`attraction`/`hotel` to `tourism`, anything else
  still falls back to `amenity`. Also discovered and fixed a second layer
  of the same bug while verifying: beaches are usually mapped as a `way`
  (a shape), not a `node` (a point), so the query itself had to change
  from `node[...]` to `nwr[...]` (node, way, or relation), and `out;` to
  `out center;`, since a way has no single lat/lon of its own, only a
  computed center point. Verified with real Miami beaches, 8 real results,
  correctly named ones sorted first, and confirmed restaurants still work
  unchanged.
  (2) and (3) fixed together with one system message rewrite: Groq is now
  told explicitly that an "out of allowed range" date error is permanent,
  not to retry it, and to never let one failed tool call cause it to
  abandon the whole answer, always report every real result it did get.
  Reran the identical Miami question: this time it tried `beach` (an
  honest empty result, Miami Beach is a separate island several miles from
  downtown, outside our default 800m search radius, a real reason, not a
  bug), correctly skipped retrying the doomed forecast call and used
  `get_weather` instead, tried `attraction` on its own initiative and got
  4 real results, and the final answer reported all of it, real
  attractions, real current weather, and was specific and honest about
  the two parts it genuinely could not answer, instead of the blanket "I
  was unable to plan a trip for you" from before.
- That rough edge fixed too: added `CATEGORY_RADIUS` to `places.py`, the
  same pattern as `CATEGORY_TAGS`, mapping category to a sensible default
  search distance, restaurants/cafes/bars stay walkable at 800m, beaches
  get 15km, attractions/viewpoints/museums get 8km, parks/hotels get 5km.
  `radius` is no longer a required argument, if not given, the right
  default is picked automatically based on category. Verified with real
  data: searching "beach" near downtown Miami with no radius specified now
  correctly surfaces Miami Beach, South Pointe Beach, and Crandon Beach,
  real, famous, named beaches, not the empty result from before. Confirmed
  restaurants are completely unaffected, same 10 results as before the
  change, since only the categories that needed a wider net got one.

- Phase 6.2 done, real day-by-day itinerary structure. Verified WMO
  weather codes directly against Open-Meteo's own docs before writing
  anything, rather than trusting memory: codes 51-67, 80-82, and 95-99 all
  mean rain, drizzle, showers, or thunderstorms, 0-3 are clear to overcast
  with no precipitation. Extended the system message: structure multi-day
  answers as one clearly labeled section per date, respect arrival time on
  day 1 and departure time on the last day, and use each day's real
  `weather_code` to suggest indoor options or an umbrella on rain-coded
  days. Tested with a real 4-day Nashville trip, arrive Aug 15 at 3pm,
  leave Aug 18 at 11am: got back 4 real, separately labeled days, day 1
  correctly scoped to "the rest of the day" after 3pm, day 4 correctly
  scoped to before an 11am departure, each day citing its own real
  temperature and weather code. Honest gap: all 4 real days in this test
  happened to be clear or partly cloudy, so the rain/umbrella instruction
  is wired in but not yet watched firing on an actual rain-coded day,
  worth reconfirming next time a forecast in range includes real rain.

- Phase 6.2 extended with real meals, real distance, and a real cost
  lesson. Added `agent/distance.py`, `calculate_distance(lat1, lon1, lat2,
  lon2)`, the Haversine formula, real distance between two points on
  Earth's curved surface, pure math, no API, tested against two real
  Nashville restaurants (0.2 miles apart, correct). Wired in as a fifth
  tool. Extended the system message: call `find_places` for real meals
  each day, reason about a missed lunch on arrival, and when choosing
  between multiple real activity options, use `calculate_distance` for
  real numbers and weigh that against Groq's own general knowledge of how
  notable a place is, labeled honestly as reputation, not verified data.
  First attempt at this let Groq search FIVE separate categories
  unscoped, cafe, restaurant, bar, attraction, museum, which blew through
  even a raised 15,000 token budget without finishing, and triggered
  repeated `tool_use_failed` errors that got worse as the conversation
  grew longer. Root cause diagnosed correctly before fixing: this was not
  a token or rate-limit problem, it was too much unscoped autonomy for a
  free model to handle reliably in one shot. Fixed by explicitly bounding
  scope in the system message, at most 2 `find_places` calls for the
  entire trip, reused across every day, not one search per day. Retested
  against the same real question: dropped from 17,285 tokens (did not
  finish) to 9,830 (finished cleanly), real weather clothing advice fired
  (sunscreen and hat above 32C), real meal suggestions fired using real
  restaurant names. Honest remaining gaps: Overpass flaked on the
  attraction search this run, so the fallback to Groq's own general
  knowledge for attractions only got one blanket disclaimer at the end,
  not per-suggestion labeling as intended, and `calculate_distance` was
  never actually called in this run, no real two-option tradeoff moment
  came up, so that logic is still unverified in practice.
- Considered and rejected self-hosting Llama on a rented GPU server,
  including student discount programs, to remove the token budget
  problem. Reasoning kept for the record: the actual failures that day
  were `tool_use_failed` errors, the model itself producing malformed
  tool calls, a property of Llama 3.3 70B's own weights, not of Groq's
  infrastructure. Self-hosting the identical weights would reproduce the
  identical mistakes. It would also cost real, ongoing money, a 70B model
  needs a serious GPU, student credit programs are one-time grants in the
  50 to 300 dollar range, not free forever, and would become a real bill
  within days to weeks of regular use, breaking the no-spending rule. The
  free fix, scoping the task down, directly targeted the real cause and
  cost nothing.

- Added a real self-refine loop: `critique_answer` in `agent/loop.py` uses
  a second, genuinely SMALLER model, `llama-3.1-8b-instant`, same Groq
  account, no new key, to score the main model's answer against a 5-point
  rubric using only the real tool data gathered, capped at
  `MAX_REFINEMENT_ROUNDS = 2` so it can never bounce back and forth
  indefinitely. First real test exposed a genuine regression, not a win:
  cost rose to 13,734 tokens and the final answer got WORSE, no
  restaurants at all, because Overpass flaked on the restaurant search and
  Groq's revision, told only "fix what's missing," retried a completely
  different category instead of the one that actually failed. A second
  raw retry reproduced the identical failure, restaurant flaked twice in a
  row, ruling out one-off bad luck. Root cause corrected properly: added
  `find_failed_tool_calls` to `agent/loop.py`, which scans the real
  conversation for any tool result containing an "error" key and looks up
  the exact tool name and arguments that failed, so the revision message
  can name it directly and tell Groq to retry that EXACT tool, not guess.
  Also added real retry-with-backoff, `_query_overpass` in
  `agent/places.py`, up to 3 attempts with a 1 second delay, at the
  network layer itself, before a failure is ever reported to Groq at all,
  since a plain retry loop is more reliable than hoping an LLM decides to
  retry correctly, and costs zero extra tokens. Retested: Overpass flaked
  once, the network-level retry caught it silently, Groq never saw a
  failure, the critic scored 4/5 on the first pass, zero refinement
  rounds needed, cost dropped to 11,998 tokens, and the itinerary was the
  best yet, real restaurant names throughout, correct arrival/departure
  scoping, and the rain-day indoor-activity instruction firing correctly
  for the first time on a real `weather_code: 51` day. Honest note: the
  "retry the exact failed tool" instruction is still correctly wired in
  but hasn't been directly observed firing, the network-level fix
  prevented the failure from ever reaching that point in this retest.

- Phase 6.3 done, fully confirmed. `run_agent` now calls
  `get_recent_trips(limit=1)` at the start and, if a trip exists, appends
  it to the system message as context, explicitly telling Groq to use it
  only if the new question is a natural follow-up (a cuisine preference, a
  small change) and to ignore it entirely for an unrelated new trip. No
  code-side guessing about intent, that judgment is left to Groq, since a
  rigid rule would get it wrong more often than not. Deliberately scoped
  to the single most recent trip only, there is no login system yet
  (phase 12), so there is no real concept of "your" trips versus anyone
  else's, this is the honest, correctly scoped version for now, not a
  permanent design.
- First attempt genuinely mid-test discovered a real, separate limit:
  **Groq's free tier also has a 100,000 tokens/day cap**, on top of the
  6,000/minute one we already knew, hit live from this session's heavy
  testing. Further discovery: it is a rolling 24-hour window, not a fixed
  clock-time reset, a small test call succeeding does not mean a full run
  will fit yet, confirmed by watching a "used" count go up, not down,
  right after a supposed reset.
  Retested clean once real headroom existed: asked "I want good Mexican
  food specifically," no city named anywhere in the question. Groq
  correctly called `geocode_city("Nashville")` on its own, inferred
  entirely from the saved trip's context, searched real restaurants
  there, and correctly recommended Oscar's Taco Shop, a real result from
  that search, as fitting "Mexican." Final answer: "Based on the list of
  restaurants provided, I can recommend Oscar's Taco Shop for good
  Mexican food in Nashville." Real memory, confirmed end to end, not
  scripted. One small honest imperfection: its very first move was a
  `find_places` call at slightly-off, seemingly memorized coordinates
  before self-correcting to the real geocoded ones one step later, the
  same "sometimes skips geocoding first" tendency from phase 3, mostly
  fixed, still occasionally peeking through.

- Restaurant naming built: `find_place_by_name(lat, lon, name, category)`
  in `places.py`. Real testing before writing it: searching by name ALONE
  genuinely failed 3 of 4 real Overpass attempts, mostly full 30-second
  timeouts, worse than the usual quick flakiness. Combining name with a
  required category cut response time from 10-30+ seconds down to 1-4
  seconds and brought reliability back to normal, confirmed with repeated
  real tests, not assumed. Wired into `loop.py`'s tools and system message.
- A real, live bug found while testing it: the critic incorrectly claimed
  a place "was not found" when it genuinely had been, and Groq trusted the
  wrong critique over its own correct, earlier, successful tool result.
- Learned and applied the concept of a **guardrail**: a deterministic,
  code-level check that catches a model's mistake at a specific point,
  input, action, or output, rather than trusting the model to behave
  correctly. Confirmed we had already built several without the word for
  it: `today`'s real date (input), `TOKEN_BUDGET` and the step cap
  (action), `find_failed_tool_calls` (action).
- Built a new guardrail for the critic-trust bug: `extract_real_place_names`
  scans the real conversation for every place name that genuinely came
  back from a real tool result, and that list is handed to Groq during a
  refinement round as a trusted anchor the critic's prose cannot override.
- Built a second, separate guardrail for a different, real, reproducible
  bug: Groq sometimes calls a coordinate-needing tool using its own
  memorized, approximate coordinates instead of calling `geocode_city`
  first, despite the system message already saying to always geocode
  first, that instruction alone was proven unreliable, watched failing
  live twice. `has_geocoded_yet(messages)` plus a `NEEDS_REAL_COORDS` set
  now blocks `find_places`, `find_place_by_name`, `get_weather`, and
  `get_forecast` from running at all until a real, successful
  `geocode_city` call exists in the conversation, returning a synthetic
  error instead. Verified fixed with the exact question that exposed the
  bug: the premature call was correctly blocked, Groq geocoded
  immediately after, and the retry succeeded with real coordinates.
- Tuned the critic loop based on real, repeated evidence, not a guess:
  `MAX_REFINEMENT_ROUNDS` lowered from 2 to 1, since in every real test a
  second round either never got enough budget left to run, or ran and
  still failed to reach an acceptable score. `TOKEN_BUDGET` raised from
  15,000 to 18,000, since the toolset grew to 5 tools and a real,
  legitimate run needed 17,259 tokens to finish. Retested the same real
  question after both fixes: converged to a real, complete answer for the
  first time, 17,822 tokens, under budget. The critic's very last verdict
  was still factually wrong, a second confirmed instance, a different
  place this time, but capping rounds at 1 meant there was no round left
  for Groq to act on it, so the wrong critique caused no actual harm, an
  unplanned but genuinely useful side effect of the same fix.

- Real named-place search confirmed done: `find_place_by_name` works
  end to end, verified across multiple real runs, including one where it
  correctly returned `None` for a place that genuinely doesn't exist.
- Found and fixed a real, separate cost-tracking gap while investigating
  latency and tokens: `critique_answer`'s own real cost was never being
  counted anywhere. `total_tokens_used` only ever tracked the main model,
  every "total tokens" number reported all session had been undercounting
  by whatever the critic actually cost, silently. Fixed by capturing
  `response.usage.total_tokens` from the critic call itself and adding it
  to the same running total, with the same budget check applied right
  after. Verified live: the critic's real cost, 983 tokens, was correctly
  counted and correctly could trigger the budget cap on its own.
- Discovered something much more urgent while investigating that same
  cost problem: a real email, verified directly against Groq's own
  [deprecations page](https://console.groq.com/docs/deprecations), not
  taken at face value, confirmed both `llama-3.3-70b-versatile` (the main
  model, in `.env`) and `llama-3.1-8b-instant` (the critic) are being
  shut down on August 16, 2026, three days from when this was found.
  Migrated immediately: `LLM_MODEL` to `openai/gpt-oss-120b`, `CRITIC_MODEL`
  to `openai/gpt-oss-20b`, the official recommended replacements. Retested
  the same real question used throughout this whole debugging arc:
  **8,985 total tokens**, versus a previous best of 17,822 on the exact
  same question, **5/5 critic score on the first pass**, no refinement
  round needed, zero `tool_use_failed` errors, and the model used
  `calculate_distance` entirely on its own initiative for the first time
  all session, correctly, unprompted. A clean, dramatic improvement,
  confirmed with real numbers, not assumed just because it's newer.

**Next concrete action:**

The "commonly overrated" commentary idea, reconfirming the rain-day
instruction on a second real rain day, watching `calculate_distance` fire
on a real two-option tradeoff in a genuine multi-option scenario, and
per-suggestion labeling when Groq falls back to general knowledge, are
still queued, now worth reconfirming fresh against the new models rather
than assuming old results still hold. Trimming what gets sent to the
critic each round, and measuring real wall-clock latency, are also still
open, lower priority now that the new models are already meaningfully
cheaper and more reliable on their own.

**Phase 7, wardrobe, scope corrected before building.** The first version
of `agent/wardrobe.py` was too narrow, generic weather-based packing text,
no real wardrobe involved. Corrected against the real requirement: a
genuine personal stylist reasoning over Sreeja's actual real clothes, real
photos of every item (needed specifically to tell visually similar items
apart, two different black leather jackets is the concrete example that
came up), outfit suggestions by place/vibe/mood/weather, a real feedback
loop for rejected suggestions, and gap-analysis "you don't own this style,
here's what to buy" suggestions.

**Real photo source.** `closet/` in the project root, ~72 real photos,
Sreeja's actual wardrobe, a mix of flat/hanger shots and on-body mirror
shots, confirmed by directly viewing a sample rather than assuming.

**Real, verified technical finding: Groq has a free vision model.**
Checked directly against Groq's own docs rather than assumed:
[docs/vision](https://console.groq.com/docs/vision) confirms
`qwen/qwen3.6-27b`, a real multimodal model, up to 5 images per request,
20MB max image size. [docs/rate-limits](https://console.groq.com/docs/rate-limits)
confirms its free tier: 30 requests/min, 1,000 requests/day, 8,000
tokens/min, 200,000 tokens/day. This is what makes auto-drafting labels
for ~72 real photos possible without paying for a separate vision API.

**`agent/wardrobe_vision.py` built and tested.** `draft_label(photo_path)`
reads one real photo file, base64-encodes it, sends it to the vision
model with a system prompt that explicitly forbids inventing details it
cannot actually see, and asks for `category`/`color`/`style_notes` as
JSON. This is a DRAFT only, never trusted as fact on its own, since only
Sreeja actually knows if an item is "date night" versus "casual," real
review and correction happens before anything is treated as real for the
stylist agent.

Real bug hit and fixed on the first test run: `qwen3.6-27b` defaults to a
"thinking" mode, a full paragraph of reasoning before its real answer,
which is not valid JSON, so `json.loads` failed on a genuinely correct
answer and silently fell into the "unclear" fallback. Checked Groq's own
[docs/reasoning](https://console.groq.com/docs/reasoning) rather than
guessing at a fix: `reasoning_effort="none"` is a real, documented
parameter specific to this model that disables thinking mode entirely.
Fixed and reverified on the same 3 real photos: clean JSON, no wasted
reasoning tokens, cost dropped from 7,264 to 6,018 tokens for 3 images,
about 2,000 tokens per image, mostly the real cost of encoding the image
itself. At that rate, all ~72 photos costs roughly 144,000 tokens, inside
the real 200,000/day free budget but without much room to spare, so the
real batch tagging run needs to happen in one sitting, not split across
days assuming the budget just resets cleanly (see phase 6.3's rolling
24-hour window finding, still true here).

Verified the actual labels against the actual photos by eye, all 3
correct: a white floral-print camisole with tie straps, a dark grey
long-sleeve off-shoulder top, and an olive green ribbed bodycon mini
dress.

**Real storage design.** `supabase/migrations/0003_create_wardrobe_items.sql`
creates `wardrobe_items` (`id`, `file_name`, `photo_url`, `category`,
`color`, `style_notes`, `occasion_tags`, `created_at`), plus a `wardrobe`
Storage bucket, `public = true` so each real photo gets a real, permanent
URL, no auth dance needed to view your own wardrobe photos, plus the same
temporary permissive RLS pattern phase 5 used for `trips`, real per-user
policies come in phase 12. `0004_grant_wardrobe_access.sql` grants the
`anon` key `select`/`insert` on the new table, the same second gate phase
5 discovered is separate from RLS. Both written to be run by hand in the
Supabase SQL editor, same as every migration so far, this project has no
Supabase CLI installed.

**Honest, current limitation, not yet solved.** The stylist agent can
hand back a real photo's real URL, but nothing in this project can
currently display an image, `loop.py` is a pure text conversation, phase
13 (the React frontend) is what makes an actual visual answer possible.
Until then, verifying correctness means pulling up the real photo
directly during testing, and the agent's real answers reference an item
by name plus its real link.

**Migrations run, real batch cataloging under way.** Sreeja ran both
migrations in the Supabase SQL editor. `agent/wardrobe_catalog.py` built:
walks every real file in `closet/`, uploads it to the real `wardrobe`
bucket, calls `draft_label`, inserts one real row per photo into
`wardrobe_items`. Skips any `file_name` already in the table, so it is
safe to run more than once, a second run only picks up new photos.

Two real, separate bugs hit and fixed on the first live run, worth
keeping:
1. **Invalid storage key.** All 12 real `IMG_*.jpeg` photos uploaded
   fine, all 65 real screenshot photos failed with `Invalid key`, because
   their real names, like `Screenshot 2026-08-14 at 11.45.37 AM.png`,
   contain a space, which a Supabase Storage object key cannot contain.
   Fixed with `_storage_key`, replacing anything that isn't a letter,
   digit, dot, dash, or underscore with an underscore, used only for the
   real storage path, `wardrobe_items.file_name` still keeps the real,
   original, human-readable name.
2. **Partial-failure duplicate.** A batch that uploads a real photo
   FIRST, then tags it, has a real gap: if tagging fails after a real
   upload already succeeded (which is exactly what the token cap below
   caused), a retry re-attempts the upload and gets `Duplicate, resource
   already exists`, since `.upload()` refuses to overwrite by default.
   Fixed by adding `"upsert": "true"` to the real upload call, confirmed
   against the installed `FileOptions` type rather than guessed, so a
   retry is safe regardless of which real step failed last time.

**Real, hard constraint confirmed live: the 200,000 tokens/day cap
(first found in phase 6.3) is the actual limiter on this batch,** at
roughly 2,000-2,600 tokens per real photo. Watched it directly: a batch
of ~2,600 real tokens per image against a shared daily pool already
partly spent by earlier testing means the last stretch of ~30-36 photos
repeatedly hit real `429` errors. Confirmed genuinely rolling, not a
fixed clock reset, by reading Groq's own live countdown in the error
message and watching it count down in real time across repeated checks.
Because the original tokens for this batch were spent in one dense burst
within a roughly 45 minute window, the real fix is simply waiting, in
that same rough spacing, 24 hours later, for each chunk to roll back out
of the window, a few images' worth of budget at a time. Not a bug to
code around, an honest real constraint of the free tier, handled by
waiting rather than guessing at a workaround.

**Real batch complete: all 78 real photos cataloged.** Confirmed directly
against the real table, 78 rows, real public photo URLs, real draft
labels. Took far longer in wall-clock time than in actual work, almost
entirely real waiting on the token cap rolling off in small chunks, spread
over roughly 2 hours: 12 photos the first pass, then repeated short bursts
of 1-29 photos each time enough of the window cleared, confirmed by
directly reading Groq's own live countdown in each `429` and waiting that
real amount rather than guessing. Total real vision-tagging cost across
every photo, including the very first single-photo pipeline test and every
retry of an already-failed photo: **129,165 tokens**. Category breakdown,
straight from the real table: 43 tops, 11 dresses, 9 pants, 9 skirts, 3
jumpsuits, 1 cardigan, plus one real, honest data-quality issue found by
checking rather than assuming: the vision model returned `"SHORTS"` and
`"tops"` for two items instead of the lowercase singular `"top"`/`"pants"`
pattern every other row used, so a naive filter by exact category text
would silently miss them. Real, concrete reason this data needs Sreeja's
real review pass before the stylist agent trusts it, not just correcting
wrong content, normalizing inconsistent values too.

**Review pass, scope corrected again by Sreeja before it happened.** She
sampled the real photos with me directly rather than doing a manual
review pass: all 78 are confirmed her own real owned clothes, the
inspiration/influencer content she wants remembered lives separately in
her Photos screenshots and Instagram saves, not yet part of this
project, queued as its own real phase (7.5) once she gathers those into
a folder. She also corrected the occasion design directly: occasion
should never be a fixed label stored per item, the same top reads
casual or date-night depending what it's paired with, that judgment has
to happen live, per combination, which is exactly what an LLM reasoning
step is for, not a static tag. `occasion_tags` stays an unused column,
no schema change needed.

**`agent/stylist.py` built and verified end to end.** `suggest_outfit
(request, rejected_ids=None)` fetches the real `wardrobe_items` table,
hands the model a compact real listing (id/category/color/style_notes
only, no photo URLs, keeps it cheap), and asks it to pick a real,
complete outfit using only real ids, reasoning about occasion from the
specific combination chosen. A `wardrobe_by_id` lookup after the real
response, same guardrail pattern as `has_geocoded_yet`, means a
hallucinated id can never reach the user disguised as a real item.

Real, live bug found on the first honest stress test, worth keeping:
asked for "a floor-length formal gown for a black tie date night," a
real gap since nothing in the closet is floor-length. The agent instead
picked a real high-low-hem midi dress and claimed in its own reasoning
that it "reaches the floor at the back," a real fabrication, stretching
a vague style description into a specific, unconfirmed, and genuinely
false claim about a real garment's real length. Confirmed by looking at
the actual photo, mid-calf at the longest point, nowhere near the floor.
Fixed with an explicit conservative instruction: any specific, checkable
requirement (a length, a fabric, a formality level) not EXPLICITLY
confirmed in the real wardrobe data must be treated as a real gap,
`fits_request: false`, rather than rounded up to fit. Retested the exact
same request: correctly returned `fits_request: false`, a real gap_note,
and a shopping_suggestion clearly labeled as general fashion knowledge,
zero items falsely claimed. Retested a normal legitimate request
afterward too, to confirm the stricter prompt didn't break real matches,
still picked a correct, sensible casual-park outfit.

Real feedback loop verified too: asked for the same date-night request
twice, second time passing the first suggestion's real ids as
`rejected_ids`, got back a genuinely different real combination, zero
overlap with the rejected ids, confirmed by set intersection, not eyeballed.

Added `run_stylist_repl()`, a real live conversation loop, ask for an
outfit, say "no" to get a different real combination for the same
request, or ask something new to start over, so this can actually be
tried, not just read from a test script's printed output.

**Not yet done:** trying the real REPL live with Sreeja.

**Phase 7.5, the inspiration library, complete.** Sreeja gathered 22
real saved style photos into `closet/inspos/`, a real mix confirmed by
directly viewing samples: Instagram outfit posts from influencers,
personal photos of other people's styling, and real e-commerce
screenshots naming an actual product. `supabase/migrations/0005_create_
style_inspiration.sql` created a separate real table and a separate
real `inspiration` Storage bucket, kept apart from `wardrobe_items` on
purpose since these are styles she liked, never items she owns.
`agent/inspiration_vision.py` (`draft_inspiration_label`) and
`agent/inspiration_catalog.py` mirror the wardrobe pattern, drafting a
real description plus, only when actually visible in the photo, a real
`source_brand`/`source_product_name`, verified against the Primark
screenshot I'd already looked at directly, matched exactly.

Also confirmed directly by sampling a dozen of the ~65 wardrobe
screenshots across the full time range: all are genuinely Sreeja's own
real try-on photos, no inspiration content was mixed into the original
78-item wardrobe batch, so no cleanup was needed there.

Two more real, separate bugs hit and fixed on this batch, both patched
in a new shared `agent/vision_utils.py` and backported into
`wardrobe_vision.py` too, since it was the exact same underlying code,
just duplicated:
1. **Oversized real photo.** `IMG_2967.PNG`, 8.3MB, got a real `413
   Request Entity Too Large` from Groq. `encode_image_for_vision`
   resizes anything over 1568px on its longest side and re-encodes as
   JPEG before sending, real, confirmed fix, retested and that exact
   photo processed successfully afterward.
2. **Fragile JSON parsing.** `IMG_2652.PNG`'s real response had text
   surrounding the real JSON, our old check (only strips a fence at the
   very start) missed it, and the model's real, correctly-extracted
   brand and product name got swallowed whole into a fallback field
   instead of surfaced. `extract_json` now finds the first `{` and the
   last `}` in the raw response and parses only that real substring,
   which survives extra text either side. Needed a real, separate
   permission fix too: correcting the two already-bad rows needed
   `update`/`delete`, never granted, only `select`/`insert`, added via
   `0006_grant_update_delete.sql`, kept broad on purpose since Sreeja's
   own future review/correction pass needs the same real permissions.
   Retested both real rows after deleting and re-running: correct real
   description, correct real brand/product, confirmed by direct
   comparison against my own earlier reading of the same photo.

Hit the real 200,000 tokens/day cap on this batch too, same constraint
as phase 7.3, same fix, waiting for the real rolling window. One real,
useful, honestly-uncertain observation from watching it closely this
time: retrying right at the edge of the window tends to only clear
about one photo per ~20 minute wait, because the retry itself
immediately re-fills the sliver of room that just opened, while a
single longer wait (55 minutes) let all 10 remaining photos clear in
one pass. Not fully explained, Groq does not publish the real internal
bucketing of the rolling window, but real, repeated, observed behavior
worth remembering: prefer fewer, longer waits over many short ones when
this cap is hit again.

Real, honest data-quality flag surfaced for Sreeja's own review, not
silently trusted: `IMG_6158.PNG`'s real `source_product_name` ("Winter
Outfit Premium Denim Cute Strapless Raw Edge Midi Dress") does not
match its own real `description` (a rust floral blouse with denim
shorts), a real, plausible sign the model pulled a product title from
an unrelated part of the same screenshot, like a "you may also like"
row, rather than the actual pictured outfit. Also, `source_brand`
capitalization is inconsistent (`commense` vs `Commense`), same real
normalization gap already flagged for wardrobe categories.

**Phase 7.6, real virtual try-on avatar, scoped but not started.**
Sreeja asked for a real image of herself, same face/hair/body, actually
wearing recommended real outfits, closer to a Snapchat avatar or a
retail virtual try-on tool than anything built so far. Real research
done before promising anything: Groq itself has no image generation at
all (confirmed on its own docs, confusable with the unrelated "Grok"
product, which is paid anyway). Real, genuinely free leads exist
instead: Hugging Face hosts free virtual try-on demos, Kolors Virtual
Try-On, IDM-VTON, OOTDiffusion, that take a real photo of a person plus
a real photo of a garment and generate a composited image, exactly the
core of what she's asking for, and we already have both real ingredients
from phases 7.3/7.5. Two honest open questions before committing to
this: whether these free demos expose a real callable API versus only a
manual web page, and their real reliability/rate limits. Hairstyle
changes specifically are flagged as likely out of scope for
garment-focused try-on tools, a different, more general kind of image
editing, not yet verified either way.

**Stylist agent wired to `style_inspiration`, verified end to end.**
`suggest_outfit` now fetches both real tables every call, real owned
wardrobe and real saved inspiration, kept strictly separate in the
prompt: list 2 (inspiration) can be recalled and referenced by id, and
its real `source_brand`/`source_product_name` can be surfaced as a real
shopping suggestion, but its ids are explicitly forbidden from
`outfit_item_ids`, which stays owned-items-only. Same guardrail pattern
as before applied to the new field: `inspiration_reference_id` is
looked up against a real `inspiration_by_id` dict, a hallucinated id is
silently dropped, never shown as real.

Tested two real cases end to end. (1) Asked for "a relaxed monochrome
outfit for brunch, sage or olive tones": correctly recalled the real
Primark inspiration entry, correctly built the actual outfit from two
real owned items (an olive one-shoulder top, olive cargo pants), and
was explicit in its own reasoning that her real tone (olive) differs
from the inspiration's (sage), instead of overclaiming a match. (2)
Asked for "a red embroidered floor-length traditional Indian outfit for
a formal wedding," something genuinely not in her closet: correctly
returned `fits_request: false`, and instead of generic invented advice,
cited the exact real saved product, "Aachho - Marya Red Embroidered
Anokha Suit Set," pulled straight from the real inspiration entry's own
real source fields.

**Sreeja's real review pass, done.** Went through both libraries by hand
using `review.html`, corrected dozens of real category/color/style_notes
mistakes (jeans and shorts that had been mislabeled `pants`, t-shirts
mislabeled generically as `top`, several colors, navy blue and emerald
green among them, that had been drafted as plain `black`). I spot-checked
a sample against the real photos afterward and found two remaining real
issues, one genuine mislabel (a real pair of shorts still tagged `pants`,
its own style_notes said "shorts" twice) and one internal contradiction
(a striped top's color field disagreed with its own style_notes), both
fixed directly in the database and confirmed. Also checked the
inspiration library the same way: everything held up, including one
entry I had personally flagged as a likely hallucination (a SHEIN
product name that seemed to not match its own photo), which turned out
to be completely accurate once I actually scrolled down and read the
real Instagram caption in the screenshot, a real lesson in checking
fully before doubting a result.

**`review.html` extended per a real, live request:** a `product_url`
field added to `style_inspiration` (`0007_add_inspiration_url.sql`),
editable in the same review page, so a real saved style with an actual
identifiable product can carry a real buy link too, not just a
brand/product name. Left genuinely null wherever no real link exists.

**Real permission gap found and fixed while correcting these rows:**
deleting/updating a row needs `update`/`delete`, which had never been
granted, only `select`/`insert`. Fixed with
`0006_grant_update_delete.sql`, granted broadly on both real tables on
purpose, since Sreeja's own correction workflow needs exactly this.

**Phase 7's actual goal, the real agent-to-agent handoff, done and
verified end to end.** `loop.py`'s old `get_wardrobe_advice` tool
(generic, weather-only, the original narrow version) is fully replaced
by `get_outfit_suggestion`, wired to the real `stylist.py` agent built
in 7.4/7.5. `agent/wardrobe.py`, now fully superseded, deleted, nothing
else referenced it. Added `get_outfit_suggestion_for_trip` to
`stylist.py`, a clean handoff wrapper returning `(clean_result,
tokens_used)`, same 2-tuple pattern already used elsewhere, so `loop.py`
can count this real, separate agent call's cost without leaking
internal real wardrobe ids back to Groq as if they were the final
answer.

Two real, live bugs hit wiring this in, both fixed:
1. **The exact same fragile-JSON-parsing bug, a third time, in a
   completely different model.** `stylist.py` still had the OLD, naive
   parser (strip a leading fence, `json.loads`), and the MAIN model
   (`gpt-oss-120b`, not the vision one) turned out to have the identical
   real habit of surrounding its JSON with extra text. Real, live
   evidence this is a general "models don't reliably return clean JSON"
   problem, not a vision-model quirk. Fixed by reusing the same
   `extract_json` already proven twice for the vision scripts. The
   shared file was also renamed `vision_utils.py` to `llm_utils.py` at
   this point, since it stopped being vision-only the moment a
   text-only model hit the identical bug, keeping a misleading name
   would have been its own real problem.
2. **Real, evidence-based budget raise, the fourth one this project has
   needed.** `get_outfit_suggestion` is a real, separate agent call
   reasoning over dozens of real wardrobe items, ~5,000 tokens on its
   own in a real test run, genuinely more expensive than the narrow
   advice it replaced. A real run needed 20,274 tokens just to reach a
   4/5 critic score, with no budget left for its one remaining
   refinement round, watched getting cut off right there. `TOKEN_BUDGET`
   raised from 18,000 to 26,000, same evidence-based pattern as every
   previous raise, sized to real, observed cost plus real margin, not a
   round number picked in advance.

Retested the full real Nashville trip question end to end after both
fixes: a complete, real, day-by-day itinerary, real weather, real
restaurants, AND real per-day outfit suggestions referencing actual
wardrobe item ids, plus an honest real gap (no shoes cataloged yet)
with a real, clearly-labeled shopping tip, all inside the raised budget,
no refinement round even needed this time.

**Phase 7 is now genuinely complete**, including its original stated
goal, a real, working handoff between two separate agents.

**Phase 7.6, real virtual try-on avatar research, done, real conclusion:
kept manual for now.** Real, live testing, not just reading docs:

- Confirmed Groq has zero image generation capability, text and one
  vision-understanding model only, image in, text out, never the
  other direction.
- Tried calling several free Hugging Face virtual try-on Spaces for
  real via `gradio_client` (`yisol/IDM-VTON`, `levihsu/OOTDiffusion`,
  `Miragic-AI/Miragic-Virtual-Try-On`, others). Found and fixed two
  real, separate bugs of our own along the way: local file paths need
  `gradio_client`'s own `handle_file()` helper, not a bare path or
  dict, and macOS screenshot filenames again had the same hidden
  narrow-space character found earlier, fixed by resolving paths from
  a real directory listing instead of typing them by hand.
- Once those were fixed, a real call to Miragic genuinely reached their
  real GPU and ran for 121 real seconds before failing, right at the
  documented 2-minutes-per-day anonymous quota boundary, real, direct
  evidence the free anonymous tier is technically real but too short
  to finish this specific model's generation. A free (not paid,
  no-cost) Hugging Face account raises that to 5 minutes, the logical
  next real step, not yet done.
- Real privacy correction made mid-research: an early test sent
  Sreeja's actual real photo (`closet/IMG_1419.jpeg`) to one of these
  third-party Spaces before asking first, she caught this and it was
  flagged and corrected immediately. All testing after that point used
  a real, separate stand-in instead: two AI-generated avatar images she
  made herself, by hand, in Gemini (matched to her real proportions
  using real, specific posing/clothing guidance, form-fitting solid
  colors, full body, straight-on, so the avatar reflects her real
  shape), saved into `closet/avatar/`. Her real photo was never used
  in the final live tests.
- Checked whether Gemini's own real image API (`gemini-2.5-flash-image`,
  "Nano Banana", the same model she used by hand to make the avatars)
  could be called from our own code instead. Confirmed directly on
  Google's own official pricing page: genuinely **no free tier at the
  API level**, paid only, $0.30/image. The free image generation she
  used came from the separate consumer Gemini app/website, which does
  have a real free quota, but that free allowance does not extend to
  the developer API our code would need to call it automatically.

**Real decision, made by Sreeja: keep this manual for now.** She
generates outfit visuals herself, by hand, in Gemini, whenever she
wants to see one. The stylist agent's real job stays picking real
items from her real wardrobe and describing them, not generating
images. No dependency was left behind in the project from this
research, `gradio_client` was only ever an ad hoc test install, never
added to `requirements.txt`. Revisit this phase later if a genuinely
free, reliable programmatic option turns up, a real Hugging Face
account with the 5-minute quota is the most promising concrete next
step if this gets revisited.

**Phase 8 done: the orchestrator rebuilt in LangGraph, `loop.py` left
completely untouched.** By Sreeja's explicit request, this was built as
a brand new file, `agent/loop_langgraph.py`, specifically so the real
hand-built version stays a real, working, side-by-side reference, not
a git diff someone has to mentally undo to compare. `pip install
langgraph` (`langgraph-1.2.11`), and the real installed API was
checked with `inspect.signature()` before writing anything against it,
same discipline as the `mcp` SDK back in phase 9, rather than trusting
version-stale tutorial syntax.

**What got imported versus what got copied, and why, said plainly since
it matters:** every real tool, every real guardrail
(`has_geocoded_yet`, `NEEDS_REAL_COORDS`), `TOOLS`, `AVAILABLE_TOOLS`,
`critique_answer`, `find_failed_tool_calls`, `extract_real_place_names`,
`MODEL`, `MAX_REFINEMENT_ROUNDS`, the real Groq `client`, all imported
directly from `loop.py`, not reimplemented, so this file can never
quietly drift into a second, different version of logic that took real
bugs to earn. Two real, honest exceptions, both copied rather than
imported, and both are duplicated on purpose, not by oversight: the
long system message text, and `TOKEN_BUDGET`, because both are local
variables inside `loop.py`'s `run_agent` function, never exported at
module level, so there was nothing to import. Flagged clearly in
comments in the new file so future-Sreeja knows to update both places
if either real number or instruction ever changes.

**The real mapping, node by node**, this is the part with no
equivalent in the hand-built version, since the "shape" only existed
implicitly in how the `for` loop happened to behave before:
- `call_model_node`, real, direct copy of the top of the old for-loop:
  ask Groq, same 3-attempt retry.
- `route_after_model`, a real, tiny function, the exact same
  `if not reply.tool_calls:` check, just named and called automatically
  instead of inline.
- `tools_node`, real, direct copy of the old `for call in
  reply.tool_calls:` block, same guardrail, same exception handling,
  same real stylist-cost tuple-unpacking.
- `critique_node` / `route_after_critique`, real, direct copy of the
  self-refine block, same two guardrails protecting against the
  critic's own known failure modes.
- `AgentState`, a `TypedDict`, `messages` uses `operator.add` as its
  reducer (not LangGraph's `add_messages`, which expects LangChain
  message objects; ours are raw OpenAI SDK objects and plain dicts,
  exactly what `loop.py` already stores, so the simpler generic
  list-concatenation reducer is the honest, correct fit here, not
  LangChain's chat-specific one).

**Real bug hit and fixed immediately**: first run failed with
`ImportError: cannot import name 'TOKEN_BUDGET' from 'loop'`, confirming
live that it really is a local variable, not a module constant, exactly
the kind of thing worth verifying by running rather than assuming from
reading the file. Fixed by copying the real value with a comment
explaining why, not by changing `loop.py`.

**Retested the identical real Nashville question `loop.py` was tested
with, twice, on purpose, to catch both real branches:**
- First run: real, complete day-by-day itinerary, real weather, real
  restaurant names, critic scored it 4/5 and accepted it with zero
  refinement rounds needed, 17,299 total tokens. Groq chose not to call
  the stylist tool this run, real model variance, the same thing
  `loop.py` itself showed across different runs, not a bug.
- Second run: the stylist path fired this time, real tuple-unpacking
  verified working (`result, stylist_tokens = result`), real cost
  correctly added to the running total (5,528 tokens), real outfit
  returned with real photo URLs, matching what `loop.py` itself
  produced for the same handoff earlier in phase 7.
- `recursion_limit=12` passed via `config`, real, confirmed equivalent
  of the old `for step in range(12):` cap, and `GraphRecursionError`
  confirmed as the real exception LangGraph raises if that limit is
  ever hit, caught and turned into the same honest fallback message.

**A real, small, genuine simplification worth naming**: `loop.py` calls
`save_trip` from four different early-return points, one per real exit
path, easy to forget on a path nobody thought of yet. Every path through
the graph, success, budget cutoff, or a failed Groq call, converges back
to one place in `run_agent`, so there's only one `save_trip` call,
impossible to miss on a new path added later. Not a fundamental
LangGraph feature, just what naturally falls out of everything actually
funneling through one graph rather than living inside separate `return`
statements scattered through a function body.

**Teaching detour, real and thorough, before any code was written**:
built two side-by-side SVG diagrams (identical shape, different labels)
showing the manual loop and the LangGraph version drawn as the same
skeleton, corrected a real misconception (a node is not a question or a
tool, it's a plain function that reads state and returns an update),
verified who actually built LangGraph (LangChain Inc, confirmed via
search, not assumed) and why (agent workflows that need to loop and
branch, which LangChain's earlier straight-line chains couldn't do),
and worked through, using real function names, exactly which of this
project's own guardrails LangGraph does and does not remove the need
for (short answer: none of them, it only removes the generic loop
bookkeeping around them).

**Not yet done:** wiring the stylist agent as its own explicit second
node/subgraph rather than a plain tool call (a real, deeper multi-agent
graph, not required for phase 8 to be complete, `get_outfit_suggestion`
already works correctly as a tool the way it does in `loop.py`), and
comparing real wall-clock latency between the two versions, tokens are
tracked and identical in shape, latency has never been measured for
either version this whole project.

**Phase 9 done: a real FastAPI server, wrapping both real agents.**
Two real design decisions made with Sreeja before building: wrap
`loop_langgraph.py` (phase 8's version), not `loop.py`, since that's
the project's forward direction into Docker and deployment; and expose
the travel agent and the stylist agent as two SEPARATE real endpoints,
not just one, her own real reasoning: sometimes she wants full trip
planning (which already calls the stylist internally), but sometimes
she just wants an outfit for tonight with no trip involved at all, and
forcing that through the travel agent's whole system prompt would be
dishonest to what's actually being asked.

`pip install fastapi "uvicorn[standard]"`. `agent/api.py` built,
`POST /plan-trip` (real `run_agent` from phase 8), `POST /style-me`
(real `get_outfit_suggestion_for_trip`, extended with an optional
`rejected_ids` parameter so the real feedback loop works over HTTP
too), and a plain `GET /health` check. Real Pydantic models
(`TripRequest`, `StyleRequest`, `OutfitItem`, etc.) describe every
request/response shape, giving free request validation and a real,
live `/docs` page, no logic written by hand for either. Real, small
extension made to `stylist.py`'s `get_outfit_suggestion_for_trip`: now
includes each outfit item's real `id` in its response, which the
original internal tool use never needed, but a real API caller needs a
real id to send back as a future `rejected_ids` entry.

**Real incident, twice, worth recording plainly.** Tried to start the
real dev server through this session's browser-preview tooling twice,
and both times it silently launched Sreeja's separate, unrelated
portfolio project's dev server instead, despite a correctly-named,
correctly-scoped `.claude/launch.json` entry for this project. Real,
confirmed with `git status` both times: nothing in the portfolio repo
was ever touched, only a dev server process got started and stopped,
but real enough that she caught it and it needed a real, direct
apology, not a hand-wave. Switched to running `uvicorn` directly
through the terminal instead, verified with real `curl` requests, and
that tool is not being used to launch servers in this project again.

**Two real, separate bugs found live via real HTTP requests, neither
of which showed up in phase 8's direct-call testing:**

1. **`recursion_limit` counts node visits, not "rounds".** loop.py's
   `for step in range(12):` counts one Groq call as one step, however
   many tools that step results in being dispatched together.
   LangGraph's `recursion_limit` counts every single node visit, and
   our graph spends 2 node visits per real round (`call_model` then
   `tools`), so `recursion_limit=12` only ever allowed 6 real rounds,
   HALF of loop.py's real capacity. Confirmed live: a real 6-tool-call
   trip question (restaurant search, museum search, two real distance
   comparisons, the stylist call, one more) got cut off exactly at the
   12th node visit, silently, no error printed anywhere. Fixed two
   ways: doubled `recursion_limit` to 24 to match loop.py's real
   capacity, and added a real print statement to the
   `GraphRecursionError` catch block, which had none before, so this
   exact failure can never be silent again.
2. **`TOKEN_BUDGET` was too tight for a genuinely thorough real
   question.** The same real trip question, once it could run its full
   12 rounds, made MORE real tool calls than any single question had
   in earlier testing, both a restaurant AND a museum search, two real
   distance comparisons between museum options, and the stylist call,
   all in one run, a real, legitimate 28,767 tokens, confirmed by
   reading the per-step log, not guessed. Raised from 26,000 to 35,000
   with real margin, same evidence-based process as every previous
   budget raise this project. `loop.py`'s own copy of this same real
   constant was deliberately left untouched, per the standing "don't
   modify it" rule, a real, tracked, honest divergence, not an
   oversight, noted here so it's not forgotten if that file is ever
   revisited.

Retested the identical real Nashville question that exposed both bugs,
after both fixes: a real, complete, thorough itinerary, real
restaurant names, correct heat guidance, a real per-day outfit
suggestion for each day with real wardrobe item ids, and an honest
real gap noted (no summer footwear cataloged yet) with a real shopping
tip, all served correctly over real HTTP through `/plan-trip`.
`/style-me` and its real feedback loop (`rejected_ids`) also verified
directly over HTTP, genuinely different real items returned on the
second call, zero overlap with what was rejected.

**Not yet done:** the real `/docs` Swagger page has not been opened
and clicked through together yet.

**Phase 10, Docker: done and verified.** `Dockerfile` written, real
Python 3.12-slim base, dependency install cached as its own real
layer, `.env` deliberately never copied in, real secrets get injected
at run time instead, exactly the way Render will do it. One real
Docker warning fixed properly: shell-form `CMD` let `$PORT` expand but
broke Docker's real OS-signal forwarding, fixed with `CMD ["sh", "-c",
"..."]`, gets both real things at once. Docker Desktop itself needed a
real, one-time manual setup (a `brew install` hiccup, `hdiutil` "resource
busy" on the first attempt, resolved by a plain retry, then a real,
one-time password prompt to finish install). Built and ran the real
image locally, hit it with real `curl` requests, including a real
`/style-me` call that genuinely reached Groq and Supabase from inside
the container, confirmed identical to running it directly.

**Real, serious security incident found and fixed mid-phase, before any
of this got deployed anywhere.** Sreeja asked directly whether her real
wardrobe/inspiration photos, actual mirror selfies with her face, were
actually private, and the honest answer was no. Both Storage buckets
had been created `public = true` back in phase 7, with the same
`temporary_allow_all` policy pattern used everywhere since phase 5,
reasonable for `trips` (low-stakes text), never re-examined once real
photos entered the picture. A public bucket serves any file to anyone
with the URL, no key checked at all, and the permissive policy on top
of that meant the app's own public key could `list` every file in the
bucket too, not just fetch a known link.

Fixed properly, not just patched: `0008_lock_down_photo_storage.sql`
flips both buckets to private and drops the permissive policies
entirely. Verified live with a real `curl`, confirmed against a real
CDN-cache false negative along the way (first check showed a stale
`200`, a fresh cache-busted request correctly returned Supabase's real
`"Bucket not found"`, its own deliberate, honest non-confirmation
response for a private bucket accessed the old public way).

**Real, correct fix built on top, matching how a real production app
actually protects private files:** a genuinely separate, privileged
Supabase key (`SUPABASE_SERVICE_KEY`), which only ever lives in the
real backend's own `.env`, never a browser, never `review.html`, never
git. New file `agent/photo_access.py` holds the one real
`service_client` in the whole project and `sign_photo_url()`, which
turns an old, now-dead "public" URL string back into a real, temporary
signed link (1 real hour), using the bucket+path it can still parse out
of that old string. Real, live compatibility bug hit immediately:
Supabase's newest key format (`sb_secret_...`) isn't a JWT, and the
installed `supabase-py` (2.31.0, already latest) sends it somewhere
still expecting one, a real, confirmed, currently-open gap in the
library, not something a local fix or upgrade could close. Fell back to
the real, still-fully-supported legacy `service_role` JWT key instead,
confirmed working immediately. A second real, separate gap surfaced
right after: the service role key bypasses RLS by design, but table
grants are a completely separate gate, the exact same lesson phase 5
already taught with the anon key, `wardrobe_items`/`style_inspiration`
never had an explicit `service_role` grant, fixed with
`0009_grant_service_role_read.sql`.

Every real call site updated to match: `stylist.py` signs every real
photo URL at its one real exit point (`get_outfit_suggestion_for_trip`)
and in the REPL's own print path, so no caller can forget. Both catalog
scripts (`wardrobe_catalog.py`, `inspiration_catalog.py`) now upload
through `service_client`, the anon key has zero storage rights left on
purpose. `api.py` gained two new real endpoints, `GET /wardrobe` and
`GET /inspiration`, that return every real row with a fresh signed URL,
plus permissive local-only CORS so `review.html` (a plain static file
with no backend of its own) can call them. `review.html` itself
switched its real photo-loading calls to those new endpoints, saving
edits still goes straight to Supabase with the plain public key, since
that only ever touches real text fields, never a photo, and was never
part of the real exposure. Verified end to end: all 78 real wardrobe
items and all 22 real inspiration items load with working real signed
URLs, and the same fix carried into the Docker image and reverified
there too.

**Deployed: `wanderwear-agent`, live on Render.** Real public GitHub
repo created (`github.com/yelurusreejareddy/wanderwear-agent`), real
`.gitignore` scoping out `closet/` (actual personal photos) and `.env`
before the first push, one real git hiccup (GitHub had auto-created a
LICENSE file on repo creation, fixed with `git fetch` +
`git merge --allow-unrelated-histories`), verified afterward that
neither `.env` nor `closet/` made it to the remote. Render's free web
service tier picked up the `Dockerfile` automatically, real environment
variables entered by hand in Render's dashboard (never committed), a
real Health Check Path pointed at `/health`, Auto-Deploy on every push
to `main` turned on. Verified live end to end: `/docs` loads, a real
`/style-me` call over the public internet returned a correct outfit
with a working real signed photo URL. An early `curl /health` returning
404/405 was investigated, not assumed to be a real bug, cross-checked
against `/openapi.json` (route genuinely registered) and Render's own
logs (real, continuous `200 OK` from Render's internal health monitor)
before concluding it was transient DNS/edge propagation during rollout,
not a real fault.

**Phase 11, real tests: done and verified.** Before wiring up GitHub
Actions CI/CD, wrote real, passing tests first rather than starting
automation with nothing for it to actually check. `tests/test_distance.py`
and `tests/test_llm_utils.py` are pure unit tests, no API, no network,
no env vars, testing `calculate_distance` against a real known
Chicago-to-New-York distance and `extract_json` against the real
IMG_2652.PNG-shaped bug (JSON wrapped in extra text) it was written to
fix. `tests/test_api.py` uses FastAPI's own `TestClient` to hit
`/health` and to confirm Pydantic request validation on `/plan-trip`
and `/style-me` genuinely rejects a bad request (real 422), without
ever calling the real Groq or Supabase APIs, that would cost real
tokens and be flaky in CI. `tests/conftest.py` sets fake, clearly-fake
env vars before `api.py` imports, a real, live-confirmed necessity:
`loop.py` builds a real `OpenAI` client at import time and genuinely
raises immediately if `LLM_API_KEY` is missing, so importing `api.py`
in CI with no real `.env` would crash before a single test could even
run. One real bug found running these for the first time: FastAPI's
`TestClient` re-raises an in-endpoint exception by default instead of
turning it into a real 500 response, so calling `/style-me` with the
fake test Supabase URL (which genuinely fails to resolve in DNS)
failed the test for the wrong reason; fixed with
`TestClient(app, raise_server_exceptions=False)`. All 12 real tests
pass locally (`pytest tests/`).

**A real TDD pass, red then green, before CI/CD gets wired up.** Two
more real gaps found, not fabricated ones: `calculate_distance` had no
bounds check, so an out-of-range latitude/longitude (999, or -200)
would silently compute a meaningless number instead of failing, a real
risk since these coordinates can come from an LLM's own tool call.
`/style-me`'s `rejected_ids` had no constraint at all, so a negative
number, never a real Supabase row id, was silently accepted and passed
downstream instead of rejected. Wrote the real tests for the desired
behavior FIRST (`test_invalid_latitude_raises`,
`test_invalid_longitude_raises`, `test_style_me_rejects_negative_rejected_id`),
ran the suite, watched all three genuinely fail (12 passed, 3 failed),
a real red build. Then wrote the real fixes: `distance.py` now raises
`ValueError` outside real lat/lon bounds, `api.py`'s `StyleRequest`
now constrains `rejected_ids` to `Annotated[int, Field(gt=0)]`. Reran,
all 15 passed, a real green build. This is the exact same red-then-green
cycle GitHub Actions will show automatically once phase 11's workflow
is wired up, just run by hand first, once, to see it directly before
automating it.

**Phase 11, GitHub Actions: done and verified.**
`.github/workflows/tests.yml` added, a real, standard GitHub Actions
workflow, `actions/checkout` then `actions/setup-python`, both
GitHub's own official actions, installs `requirements.txt`, then runs
`pytest tests/ -v`. Triggers on every real `push` and every real
`pull_request`. Runs with zero real secrets, on purpose:
`tests/conftest.py` already sets fake, clearly-fake env vars, and none
of the 15 real tests ever call the real Groq or Supabase APIs, so
GitHub's servers never need any of this project's actual credentials
to run them. Free for a public repo like `wanderwear-agent`, GitHub
does not count public-repo minutes against any quota at all, no card,
no real cost, matching the project's no-spend rule.

**Phase 12, real Supabase Auth + per-user RLS: done and verified end
to end.** Went with the full, real multi-user version, not an
admin-only shortcut, since the real goal is eventually letting someone
else use their own copy safely. Real account created directly in
Supabase's Auth dashboard (not through any public signup flow, none
exists yet). Migration `0010_add_user_id_and_per_user_rls.sql`: added
`user_id uuid references auth.users(id)` to `trips`, `wardrobe_items`,
`style_inspiration`, backfilled every existing real row with Sreeja's
real new account id, made the column `not null` with no default on
purpose (a silent default would keep assigning a second real user's
data to the wrong account), replaced every `temporary_allow_all_access`
policy with `auth.uid() = user_id`.

New `agent/auth_context.py`: real per-request identity via Python's
own `contextvars.ContextVar`, not a shared mutable client, which would
be a genuine, live concurrency bug the moment two real users' requests
land close together. `api.py`'s new `require_user` dependency verifies
a real, valid token against Supabase itself, builds a fresh
per-request client carrying that exact token, and stores it in the
ContextVar. `memory.py` and `stylist.py` read it back internally
(`get_client()`/`get_user_id()`), so their own function signatures,
and every call site inside `loop.py` (deliberately never touched, same
rule as phase 8), never had to change at all. `wardrobe_catalog.py`
and `inspiration_catalog.py`, real admin-only batch scripts, always
run directly by Sreeja, switched to writing through the privileged
`service_client` instead, real user id set explicitly since
`service_client` bypasses RLS by design. New `POST /login` (plain anon
client, `sign_in_with_password`) and `require_user` guard every other
real endpoint. `/wardrobe` and `/inspiration` needed one more explicit
fix: `service_client` bypasses RLS, so they now filter
`.eq("user_id", user_id)` themselves, the database's own per-user
enforcement does nothing for a privileged key. `review.html` gained a
real login screen, both its GET calls (through the API) and its PATCH
saves (straight to Supabase) needed the real, logged-in token, the old
"saving is always safe, it's just text" assumption stopped being true
the moment RLS started checking a real identity there too.

One real bug found live-testing this end to end, not assumed away: a
real, valid, logged-in request to `/style-me` failed with "permission
denied for table wardrobe_items". Table-level GRANTs, same real "two
gates" lesson as phase 5 (anon) and phase 10 (service_role), had only
ever been given to the `anon` role, but a real authenticated PostgREST
request runs as `authenticated`, a role that had never been granted
anything. Fixed with `0011_grant_authenticated_access.sql`. Retested
after the fix: real login, real 401 with no token, real 200s on
`/plan-trip`, `/style-me` (correct real outfit, real signed photo
URLs), `/wardrobe` (78 real items), `/inspiration` (22 real items),
and a real `trips` row confirmed saved with the correct real
`user_id`. `pytest tests/`, all 18 real tests updated and passing,
`test_api.py` now uses FastAPI's own `app.dependency_overrides`
pattern to test request validation independent of a live login, a
real, live bug found writing THOSE tests too: overriding
`app.dependency_overrides` is a module-level dict, set once for the
whole file, not "from this point in the file onward" as first
assumed, fixed by having each test set or clear it explicitly itself.

---

## 7. Cloud hosting and costs

**The rule this all serves.** No spending money on this project, ever,
unless explicitly decided otherwise together. Every choice below is
filtered through that rule first.

**Why Render, not AWS.** AWS is the industry standard and a real
resume-worthy skill, but its free tier has a specific danger: it requires a
credit card on file, and if you go over the free limits, it charges you
automatically. There is no hard wall that stops usage at zero dollars, only
a soft limit that turns into a bill.

Render's free tier needs no card at all. It cannot silently charge you,
because it has no payment method to charge. That is the entire reason we
start here.

**Where AWS could come in later.** Once the project already works safely
on Render, adding an AWS deployment becomes an optional extra phase, purely
so "AWS" is also a defensible resume line. Not required for the project to
be complete, and not something to add casually, since it reopens the
billing risk above. If we do it, we do it deliberately, with billing alerts
set up first.

**Every service in this project and its actual free tier limit:**

| Service | Free limit | Requires a card | Risk of surprise charge |
|---|---|---|---|
| Groq | 30 requests/min, 6,000 tokens/min, 14,400 requests/day, and 100,000 tokens/day (discovered live, mid phase 6.3, hit the real 429 after heavy testing) | No | None, it just stops answering if you hit the limit |
| Supabase | 500 MB database, 1 GB file storage | No | None |
| Render | Free web service, spins down when idle | No | None |
| Open-Meteo | Unlimited for reasonable personal use | No | None |
| OpenStreetMap | Unlimited, but asks you not to hammer it | No | None |
| GitHub Actions | Free on public repos | No | None |
| Vercel | Free tier for personal projects | No | None |

If a future step ever asks for a credit card, stop and ask before
continuing. That is a deliberate checkpoint, not a formality.

**Why not self-host Llama on a rented GPU.** Considered directly during
phase 6.2, see section 6 for the full reasoning. Short version: the real
problems we hit, `tool_use_failed` errors, were the model itself
occasionally producing malformed tool calls, a property of Llama 3.3 70B's
own trained weights, not of Groq's infrastructure. Renting a GPU and
running the identical weights ourselves would reproduce the identical
mistakes, while also costing real, ongoing money, a 70B model needs a
serious GPU, and student credit programs are one-time grants, not free
forever. The actual fix, scoping the task down, was free and fixed the
real cause.

---

## 8. Troubleshooting

What to check, in order, when something breaks. Grows as we hit real
problems. Each entry: the symptom, the likely cause, the fix.

**"No API key found" when running check_setup.py**
Cause: `.env` either doesn't exist yet, or still has the placeholder text.
Fix:
```bash
cd /Users/boo/Documents/personal-agent
cp .env.example .env
open -e .env
```
Paste your real Groq key in place of `paste_your_key_here`, save, close.

**The model answered in text instead of asking for a tool**
Cause: not every model supports tool calling, or the question was too vague
for the model to see a reason to use a tool.
Fix: check `LLM_MODEL` in `.env` matches a model Groq lists as supporting
tools. Try a more specific question that clearly needs the tool, like "what
is the weather in Chicago" rather than "hello."

**"Rate limit exceeded" or 429 error from Groq**
Cause: hit the free tier limit, 30 requests per minute or 6,000 tokens per
minute. Expected if the agent loop calls Groq many times quickly while
testing.
Fix: wait 60 seconds and try again. If this happens constantly during
normal use, it means a phase 6 safety cap (limiting tool calls per
question) is missing or too loose. Do not raise the limit by paying, fix
the loop instead.

**A tool call keeps repeating and never stops**
Cause: the agent loop has no cap on how many times it can loop, and the
model keeps asking for another tool call instead of answering.
Fix: this is exactly what phase 6 (safety limits) exists to prevent. Add a
hard maximum number of loop iterations, and if it's reached, force the
agent to answer with whatever it has instead of looping again.

**OpenStreetMap returns nothing for a place**
Cause: Nominatim (geocoding) or Overpass (places) sometimes returns empty
results for small towns or oddly spelled names.
Fix: this is a real world error case, exactly what phase 4 (self
correction) is meant to handle. The agent should notice the empty result
and either retry with a wider search radius or a cleaned up spelling, or
tell the user honestly that it found nothing rather than inventing a place.

**Render server "spins down" and the first request is slow**
Cause: Render's free tier puts an idle server to sleep after inactivity.
The next request has to wake it up, which takes extra seconds.
Fix: expected free tier behavior, not a bug. Nothing to fix.

**Supabase connection fails**
Cause: usually a wrong project URL or key in `.env`, or the free project
went inactive from being unused too long.
Fix: double check the URL and key against the Supabase project dashboard.
If the project paused itself from inactivity, there is a restart button on
the dashboard.

**"bad interpreter: no such file or directory" when running .venv/bin/pip**
Cause: the virtual environment remembers the exact folder path it was
created in. If the project folder gets renamed or moved, every script
inside `.venv` still points at the old path and breaks.
Fix: delete and recreate it at the new location:
```bash
cd /Users/boo/Documents/personal-agent
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
This happened once already, when the project folder was renamed from
`sql-agent` to `personal-agent`.

**General first steps for any unexplained error:**
1. Read the actual error message fully, top to bottom, before assuming.
2. Check `.env` has real values, not placeholders.
3. Check which phase this belongs to in section 5, an error from a phase we
   haven't reached yet usually means a setup step was skipped.
4. Add the new problem and its fix to this section once solved, so it never
   has to be re-solved from scratch.

---

## 9. MCP (Model Context Protocol)

**What it is.** MCP is a standard, shared shape for describing a tool to an
AI agent. Think of it like USB-C. Before USB-C, every phone brand needed its
own charger and cable. USB-C made one plug shape that works everywhere. MCP
does the same job for connecting an agent to tools and data: build the
connector once, any agent that speaks MCP can use it, not just the one
program it was written for.

**Why we are not starting with it.** In phases 1 through 3, we write tools
as plain Python functions and wire them into our own agent code by hand.
That is deliberate, hand-wiring is how you actually learn what a tool is,
what it needs, and what it returns. If we started with MCP, the wiring
would be handled for us and would stay a black box, the same reason we
build the loop by hand before adding LangGraph in phase 8.

**Where it fits later.** Once our own tools, weather, geocoding, places,
work by hand, we repackage them as an MCP server. That means any future
agent, even one outside this project, could plug into the same tools
without us rewriting them. This becomes a real, defensible resume line, not
a buzzword, because we will have used it after understanding what it
replaces.

**The plan, confirmed: both directions, not just one.** (1) Swap one of
our own hand-built tools, likely `weather.py` or `forecast.py`, for
talking to a real, existing MCP server instead, confirmed to actually
exist and be free:
[weather-mcp](https://github.com/weather-mcp/weather-mcp), built on
Open-Meteo, the exact same source we already use, no API key, no signup.
This is what being an MCP *client* looks like. (2) Wrap our own tools,
`geocode_city`, `get_forecast`, `find_places`, `calculate_distance`,
behind the MCP protocol ourselves, so any other MCP-speaking agent could
use them, not just our own `loop.py`. This is what being an MCP
*provider* looks like. Doing both means understanding the protocol from
both sides of the connection, not just one.

**You are already looking at a working example.** The tools I am using to
help you right now in this conversation, search, file reading, the diagrams
I've drawn you, are themselves MCP servers Claude Code is connected to.

**Progress: our own server, built and verified.** Installed the official
`mcp` Python SDK (`pip install "mcp[cli]"`), checked the real installed
API directly with `inspect.signature()` rather than trusting a web
summary, since it didn't match exactly (the real class is `MCPServer`
from `mcp.server`, with a `.tool()` decorator and a `.run(transport=...)`
method). Built `agent/mcp_server.py`, wrapping the existing `geocode_city`
function with `@server.tool()`, zero new tool logic written, just a
wrapper around code that already worked. Verified end to end with a real
in-process `Client`: `list_tools()` correctly auto-generated the tool's
name and description straight from `geocode_city`'s own docstring, proven
directly with `inspect.signature()` and `.__doc__` on the real function
beforehand, and `call_tool("geocode", {"city_name": "Nashville"})`
correctly returned real Nashville coordinates through the actual
protocol, not a simulation. One real debugging moment worth keeping: the
result's `structured_content` field was `None`, which looked like failure
at first, the real data was sitting in `content` instead, a plain
wrong-field mistake, not a bug in the server.

**Extended to the full toolset.** A real MCP server isn't limited to one
tool, and a single MCP client can connect to several different MCP
servers at once, drawing tools from all of them. Added `find_places` and
`calculate_distance` to our own `mcp_server.py`, same pattern, zero new
tool logic, just the `@server.tool()` wrapper around code that already
worked. Verified all three together: tool listing showed all three with
correctly auto-generated descriptions, `places()` correctly returned real
restaurant data (and hit, then correctly recovered from, the same real
Overpass flakiness we've seen all session, proof the retry-with-backoff
logic still works when called through MCP, not just directly), and
`distance()` correctly returned `0.2` miles, matching our earlier known
result for the same two coordinates. Deliberately did not wrap
`get_weather`/`get_forecast` here, those are the two tools we plan to
replace with the real `weather-mcp` server instead, once we build the
client side.

**Decision: skip `weather-mcp`, do both roles against our own server
instead.** Discussed the real tradeoff honestly: consuming `weather-mcp`
would mean adding Node.js as a second language and toolchain, for a
result functionally redundant with our own already-working, deeply
tested `weather.py`/`forecast.py`. Chose instead to wrap the weather
tools into our own server too, same simple pattern as the other three,
and separately write a genuine subprocess-based MCP client against our
**own** server, to experience the client role for real without needing
a second language. `mcp_server.py` now wraps all 5 tools: `geocode`,
`weather`, `forecast`, `places`, `distance`.
`mcp_client_test.py` uses `StdioServerParameters` and `stdio_client` to
actually launch `mcp_server.py` as its own separate operating-system
process, not the in-process shortcut used for the first test, and talks
to it purely through stdin and stdout, the same mechanics connecting to
someone else's real MCP server would require. Verified end to end: all 5
tools listed correctly with auto-generated descriptions, and a real
`geocode` call for Chicago returned real coordinates through the actual
protocol, subprocess and all.

**FastAPI vs the MCP SDK, not the same job.** Confirmed this distinction
explicitly since it's easy to blur: FastAPI (phase 9) builds an ordinary
HTTP server for our own React frontend to call. The `mcp` SDK builds a
server that follows the MCP specification's own message format, mostly
over stdio, with an HTTP-based transport option (`"streamable-http"`)
available for a future remote deployment, still handled by the `mcp`
SDK itself, not by FastAPI underneath it. Different audiences: FastAPI
serves our own frontend, MCP serves other AI agents wanting to reuse our
tools without touching our source code.

**What 2026 interviews actually ask about it.** Based on current interview
guides, MCP questions go past "what is it" and into real depth: the
difference between a tool and a resource, how a stateless protocol changes
deployment (directly relevant to our FastAPI and Docker phases), and
security failure modes such as prompt injection arriving hidden inside a
tool's returned data, or one tool's name shadowing another's. We will meet
these concretely when we build our own MCP server, not as abstract trivia.

Sources: [MCP Interview Questions, DataCamp](https://www.datacamp.com/blog/mcp-interview-questions), [MCP Interview Questions, Interview Baba](https://interviewbaba.com/mcp-interview-questions/), [How to Crack MCP and Agentic AI Interviews, techinterview.net](https://www.techinterview.net/blog/model-context-protocol-agentic-ai-interview)

---

## 10. Reading agent/loop.py, for a total beginner

This section explains `agent/loop.py`, our first real agent, in plain
language. You do not need to know Python to follow this section, every idea
is explained from the ground up. If you do know Python, this is still the
exact explanation used when it was written.

A quick vocabulary check before starting, since the rest of this section
leans on these words constantly:

- A **list** is an ordered collection of items, written with square
  brackets, like `[1, 2, 3]`.
- A **dictionary** is a collection of labeled items, written with curly
  braces, like `{"name": "Sreeja", "city": "Chicago"}`. Each label (called a
  key) points at a value, the same way a real dictionary maps a word to its
  definition.
- A **function** is a named, reusable block of instructions that does one
  job, and can be run again and again with different input.
- **JSON** is a specific way of writing lists and dictionaries as plain
  text, so they can travel over the internet. Most APIs speak JSON.

### Where this tool description format actually comes from

Nothing about the shape of the `TOOLS` list was invented or guessed. It
comes directly from Groq's own published documentation. Here is the exact
structure Groq documents for describing a tool:

```json
{
  "type": "function",
  "function": {
    "name": "function_identifier",
    "description": "Helps model decide when to use this tool",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {"type": "string", "description": "Parameter description"}
      },
      "required": ["param_name"]
    }
  }
}
```

Our own `TOOLS` list in `agent/loop.py` follows this exact shape. Groq's
documentation also states the platform offers "OpenAI Compatibility,"
meaning Groq deliberately built its service to accept the same request
format that OpenAI's API expects. That is the real reason our project uses
the `openai` Python package even though we are talking to Groq, not OpenAI,
the package itself only cares that the server on the other end speaks the
same agreed format, the same idea as a USB-C cable working across different
phone brands.

Source: [Groq tool use documentation](https://console.groq.com/docs/tool-use)

### The file, section by section

**Describing the tools.** The `TOOLS` list is a description of our two
functions, `geocode_city` and `get_weather`, written in a format Groq can
read. It does not run anything by itself, it is pure documentation, handed
to Groq so it knows what tools exist, what each one does (the
`"description"`), and exactly what information each one needs
(`"parameters"`).

**Naming the real functions.** Groq can only ever send back a tool's name
as plain text, like the word `"geocode_city"`. Plain text cannot be run as
code. `AVAILABLE_TOOLS` is a dictionary that solves this: it maps that text
name back to the real, actual function, so our code can look up
`"geocode_city"` and get back something it can actually call.

**Starting the conversation.** `messages` is a list that holds the entire
conversation as it happens. Every item in it is a dictionary with a
`"role"` (who is speaking, the user, Groq itself, or a tool's result) and
`"content"` (what was said). It starts with just the user's question.

**The safety loop.** The whole exchange happens inside a loop that can run
at most 5 times. This exists so that if something ever goes wrong and Groq
keeps asking for more tools forever, the program cannot run endlessly or
burn through the free usage limit, it will stop and give an apologetic
answer instead.

**Asking Groq to think.** Each time through the loop, we send Groq the
whole conversation so far, plus the tool descriptions, and wait for its
reply. Groq can send back more than one possible answer at once, in a list
called `choices`, we always take the first one, since it's the one Groq
considers best.

**Remembering what Groq said.** Whatever Groq just replied gets added onto
the end of the conversation list, so that the next time we ask it something,
it can see its own earlier reasoning too, not just the original question.

**Deciding whether to stop.** If Groq's reply did not ask for any tool, that
means it believes it already has enough information to answer, so the loop
ends and the plain English answer is handed back immediately.

**Running the tool Groq asked for.** If Groq did ask for a tool, we read
which one by name, convert the arguments it sent (which arrive as text)
into real usable data, look up the real function using `AVAILABLE_TOOLS`,
and actually run it. This is the only point in the whole file where
anything real happens outside of Groq, an actual website gets contacted, an
actual answer comes back.

**Sending the real result back.** The real result gets converted back into
text and added to the conversation, labeled as coming from a "tool," along
with a matching ticket number so Groq knows exactly which of its own
requests this result answers. Then the loop goes around again, and Groq
gets to think again, now with real information it did not have a moment
ago.

### Tracing one real question, value by value

Question asked: **"What's the weather like in Nashville right now?"**

**Before the loop starts.** The conversation holds just one item: the user
asking the question above.

**Loop, first pass.** Groq reads the question. It has no coordinates yet,
so it cannot check the weather, but it can look up a city. It asks to run
`geocode_city` with `city_name` set to `"Nashville"`. That real function
runs, contacts Nominatim for real, and returns:
```
{"city": "Nashville", "lat": 36.1622767, "lon": -86.7742984,
 "display_name": "Nashville, Davidson County, Middle Tennessee, Tennessee, United States"}
```
That result is added to the conversation.

**Loop, second pass.** Groq now sees the whole conversation, including
those real coordinates. It reasons that `get_weather` needs a latitude and
longitude, and it now has both, so it asks to run `get_weather` with
`lat` set to `36.1622767` and `lon` set to `-86.7742984`. That real function
runs, contacts Open-Meteo for real, and returns:
```
{"temperature_2m": 21.8, "weather_code": 3}
```
That result is also added to the conversation.

**Loop, third pass.** Groq now sees the original question and both real
results. It decides it has everything it needs, so this time it does not
ask for a tool. The loop ends, and the final answer is handed back:

> "The current temperature in Nashville is 21.8°C and the weather code is
> 3, which indicates a partly cloudy sky."

At no point did our own code decide the order of `geocode_city` then
`get_weather`, that order came entirely from Groq reasoning about what
information it still needed. That reasoning is the actual "agent" part of
this whole project.
