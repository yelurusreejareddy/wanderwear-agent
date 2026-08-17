"""
loop.py -- phase 2: the real think, act, observe loop, written by hand.
Groq decides which tool to call. Our own code runs the tool and sends the
result back. No framework here, just Python and the Groq client.
"""
import datetime
import json
import os

from dotenv import load_dotenv
from openai import BadRequestError, OpenAI

from geocode import geocode_city
from weather import get_weather
from forecast import get_forecast
from places import find_places, find_place_by_name
from memory import get_recent_trips, save_trip
from distance import calculate_distance
from stylist import get_outfit_suggestion_for_trip

load_dotenv()

client = OpenAI(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_BASE_URL"))
MODEL = os.getenv("LLM_MODEL")

# Phase 6.2 addition: a second, SMALLER model, on the same Groq account, no
# new key, no new provider, used only to check the main model's answer,
# never to plan anything itself. A critic needs no tools at all, just
# reading text, which sidesteps the tool_use_failed problem entirely.
CRITIC_MODEL = "openai/gpt-oss-20b"

# A refinement round means Groq tries again after real feedback. This is
# capped for the same reason the step and token budgets are: without a
# hard limit, an imperfect critic and an imperfect answer could bounce
# back and forth indefinitely, burning real quota for no guaranteed gain.
# Lowered from 2 to 1, based on repeated real evidence, not a guess: in
# every real test run where a second round happened, it either never got
# enough budget left to actually run, or it ran and still failed to reach
# an acceptable score, adding real cost with no measured benefit.
MAX_REFINEMENT_ROUNDS = 1

RUBRIC = (
    "Score the ANSWER below against these 5 criteria, using ONLY the real "
    "tool results provided, not outside knowledge. One point each, 5 total.\n"
    "1. Uses real restaurant or meal names that actually appear in the "
    "tool results, does not invent restaurant names.\n"
    "2. Respects any arrival and departure time mentioned in the "
    "question, does not schedule before arrival or after departure.\n"
    "3. References real weather data from the tool results, not invented "
    "weather.\n"
    "4. Any place mentioned that does NOT appear in the tool results is "
    "clearly labeled as general knowledge, not presented as verified.\n"
    "5. If the question spans more than one day, the answer is structured "
    "as a clear day-by-day itinerary.\n"
    "Reply in exactly this format, nothing else:\n"
    "SCORE: <number out of 5>\n"
    "MISSING: <one short sentence per failed criterion, or \"none\" if all passed>"
)


def critique_answer(question, tool_results_text, answer):
    """Ask the small critic model to score the real answer against the
    rubric, using only the real tool results, not its own knowledge.
    Returns (score, feedback_text)."""
    critic_messages = [
        {
            "role": "system",
            "content": (
                "You are a strict fact-checker reviewing a trip itinerary. "
                "You do not plan trips yourself, you only verify the "
                "answer below against the real data it should be based on."
            ),
        },
        {
            "role": "user",
            "content": (
                f"ORIGINAL QUESTION:\n{question}\n\n"
                f"REAL TOOL RESULTS GATHERED:\n{tool_results_text}\n\n"
                f"ANSWER TO CHECK:\n{answer}\n\n"
                f"{RUBRIC}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=CRITIC_MODEL,
        messages=critic_messages,
    )
    reply = response.choices[0].message.content

    # Real gap this fixes: this call's own real cost was never being
    # counted anywhere before. Every "total tokens" number reported all
    # session undercounted, since the critic runs once or twice per
    # question and its real cost was silently dropped every time.
    critic_tokens_used = response.usage.total_tokens

    # Crude but honest parsing: find the line starting with "SCORE" and
    # pull the first digit out of it. If the critic didn't follow the
    # format, score defaults to 0, treated as a failed check, not a crash.
    score = 0
    for line in reply.splitlines():
        if line.strip().upper().startswith("SCORE"):
            digits = "".join(c for c in line if c.isdigit())
            if digits:
                score = int(digits[0])

    return score, reply, critic_tokens_used


def find_failed_tool_calls(messages):
    """Look back through the real conversation and find any tool call that
    actually failed, an 'error' key in its real result. Returns a list of
    (tool_name, tool_args) for each one. This exists because, without it,
    Groq had to GUESS which tool to retry after the critic pointed out
    something was missing, and we watched it guess wrong twice, retrying a
    different category instead of the one that actually failed."""

    # First pass: remember every tool call Groq asked for, by its ID, so
    # we can look the name and arguments back up once we find a failure.
    calls_by_id = {}
    for message in messages:
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                calls_by_id[call.id] = (call.function.name, call.function.arguments)

    # Second pass: find real tool results that failed, and look up which
    # call they belonged to using the ID they were tagged with.
    failed = []
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "tool":
            if '"error"' in message["content"]:
                call_id = message["tool_call_id"]
                if call_id in calls_by_id:
                    failed.append(calls_by_id[call_id])

    return failed


def extract_real_place_names(messages):
    """Look back through the real conversation and collect every real place
    name that actually came back from find_places or find_place_by_name.
    This is a real, code-verified ground truth, not a guess or an opinion,
    used to catch the critic model when it gets a fact wrong. Real example
    that exposed the need for this: the critic once claimed a place "was
    not found" when it genuinely had been, and Groq trusted that wrong
    claim over its own correct, earlier, successful result."""

    names = set()
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "tool":
            try:
                result = json.loads(message["content"])
            except json.JSONDecodeError:
                continue

            # find_places returns a list of place dicts, find_place_by_name
            # returns one place dict directly, this handles both shapes.
            items = result if isinstance(result, list) else [result]
            for item in items:
                if isinstance(item, dict) and "name" in item:
                    names.add(item["name"])

    return names


def has_geocoded_yet(messages):
    """Check whether geocode_city has already succeeded somewhere in this
    real conversation. Real, reproducible bug this fixes: Groq sometimes
    calls a tool needing coordinates using its own memorized, approximate
    guess instead of calling geocode_city first, even though the system
    message already says to always geocode first. That instruction alone
    was not reliable, watched it fail live, this is the code-level
    guardrail instead of hoping the prompt gets followed."""

    calls_by_id = {}
    for message in messages:
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                calls_by_id[call.id] = call.function.name

    for message in messages:
        if isinstance(message, dict) and message.get("role") == "tool":
            call_id = message["tool_call_id"]
            if calls_by_id.get(call_id) == "geocode_city" and '"error"' not in message["content"]:
                return True

    return False


# Tools that need a real latitude and longitude for "the place being asked
# about", not two already-found places (calculate_distance takes those
# from real search results already, so it does not need this check).
NEEDS_REAL_COORDS = {"find_places", "find_place_by_name", "get_weather", "get_forecast"}


# Groq needs a plain description of each tool: its name, what it does, and
# what arguments it takes. This does not run anything by itself, it is
# just documentation that Groq reads before deciding what to ask for.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "geocode_city",
            "description": "Turn a city name into its latitude and longitude.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city_name": {"type": "string", "description": "City name, e.g. Nashville"},
                },
                "required": ["city_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current temperature and weather code for a latitude and longitude, right now only. Cannot answer questions about a future date, use get_forecast for that.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude"},
                    "lon": {"type": "number", "description": "Longitude"},
                },
                "required": ["lat", "lon"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get the daily high, low, and weather code for a latitude and longitude, for a future date range. Use this for any question about a specific future date, like next weekend or a trip.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude"},
                    "lon": {"type": "number", "description": "Longitude"},
                    "start_date": {"type": "string", "description": "First day, format YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "Last day, format YYYY-MM-DD"},
                },
                "required": ["lat", "lon", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_places",
            "description": "Find real nearby places of a given category near a latitude and longitude. Returns up to 10 of the most completely documented listings from OpenStreetMap. This is NOT a rating or popularity ranking, real ratings are not available, never describe these results as top-rated, best, or highly reviewed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude"},
                    "lon": {"type": "number", "description": "Longitude"},
                    "category": {"type": "string", "description": "One of: restaurant, cafe, bar, beach, park, museum, viewpoint, attraction, hotel"},
                },
                "required": ["lat", "lon", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_place_by_name",
            "description": "Look up ONE specific place by its real name, for when the user names an exact restaurant or place they want, instead of a general category. Returns the real place if found, or nothing if it does not exist near that location. category is required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude"},
                    "lon": {"type": "number", "description": "Longitude"},
                    "name": {"type": "string", "description": "The specific place name the user mentioned"},
                    "category": {"type": "string", "description": "One of: restaurant, cafe, bar, beach, park, museum, viewpoint, attraction, hotel"},
                },
                "required": ["lat", "lon", "name", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_outfit_suggestion",
            "description": "Ask a separate real stylist agent to suggest a real outfit, from the user's actual owned wardrobe, for part of this trip. The stylist reasons over her real closet and her real saved style inspiration, and will honestly say so if nothing she owns fits, with a real shopping suggestion instead of forcing a bad match. Call this only after you have real day-by-day weather from get_forecast, and pass it a real, plain-English request describing the actual weather, destination, and occasion/vibe, do not invent conditions to send it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request": {"type": "string", "description": "Plain-English real request: place, occasion/vibe, and the REAL weather already gathered"},
                },
                "required": ["request"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_distance",
            "description": "Get the real distance in miles between two latitude/longitude points. Use this to decide how far apart two stops on a trip actually are, never guess a distance yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat1": {"type": "number", "description": "First point's latitude"},
                    "lon1": {"type": "number", "description": "First point's longitude"},
                    "lat2": {"type": "number", "description": "Second point's latitude"},
                    "lon2": {"type": "number", "description": "Second point's longitude"},
                },
                "required": ["lat1", "lon1", "lat2", "lon2"],
            },
        },
    },
]

# Groq only ever sends us a tool's NAME as text, like "geocode_city".
# This dictionary is how we turn that name back into the real Python
# function we can actually call.
AVAILABLE_TOOLS = {
    "geocode_city": geocode_city,
    "get_weather": get_weather,
    "get_forecast": get_forecast,
    "find_places": find_places,
    "find_place_by_name": find_place_by_name,
    "get_outfit_suggestion": get_outfit_suggestion_for_trip,
    "calculate_distance": calculate_distance,
}


def run_agent(question):
    """Run the full think, act, observe loop for one question."""

    # Groq has no built-in sense of "today". Left alone, it guesses, and it
    # guessed 2024 for us once already. We tell it the real date ourselves,
    # using our own computer's clock, not a hardcoded guess that goes stale.
    # We also tell it to always geocode first, since it otherwise sometimes
    # uses its own memorized, slightly-off coordinates instead of our tool.
    today = datetime.date.today().isoformat()

    # Phase 6.3: real memory. Without this, every single question starts a
    # brand new conversation from zero, even though phase 5 already saves
    # each finished trip. A follow-up like "I want Mexican specifically"
    # would previously get no context at all about what trip that even
    # refers to. There is no login system yet (phase 12), so there is no
    # real concept of "your" trips versus someone else's, the honest,
    # correctly scoped version for now is: the single most recently saved
    # trip. We do not try to guess in code whether the new question is a
    # follow-up or a new trip, that is a fuzzy judgment call better left
    # to Groq's own reasoning than a rigid rule we would get wrong.
    memory_context = ""
    recent_trips = get_recent_trips(limit=1)
    if recent_trips:
        last_trip = recent_trips[0]
        memory_context = (
            f"\nFor reference, here is the most recently planned trip: "
            f"Question: {last_trip['question']} "
            f"Answer: {last_trip['answer']} "
            f"If the CURRENT question below is a natural follow-up to "
            f"that trip, like a specific cuisine request or a change to "
            f"one detail, use this context and stay consistent with it. "
            f"If the current question is about a new, unrelated trip or "
            f"destination, ignore this entirely and start fresh."
        )

    system_message = {
        "role": "system",
        "content": (
            f"Today's date is {today}. Always call geocode_city first to get "
            "exact coordinates for a place, never guess coordinates yourself. "
            "Call only one tool at a time, and always wait for its real "
            "result before deciding on the next tool. Never write a "
            "placeholder value for an argument you do not have yet. "
            "If a tool result contains an 'error' field, do not give up "
            "immediately: check whether the error was caused by something "
            "you can fix yourself, like a wrong date range, and retry once "
            "with corrected arguments. But if the error message says a date "
            "is out of an allowed range, that is a permanent limit, not a "
            "mistake you can fix, do not retry that same call again, "
            "accept it and move on immediately. "
            "Never let one failed tool call cause you to abandon the whole "
            "answer. Always use and clearly report every real result you "
            "did get from other tools, restaurants, places, or weather that "
            "did succeed, and only note the specific part that failed, by "
            "name, honestly. Do not say you were unable to help at all if "
            "you actually have real, useful information to share. "
            "When a question spans more than one day, structure your "
            "answer as a real day-by-day itinerary, one clearly labeled "
            "section per date, not one blended paragraph. If an arrival "
            "time is mentioned, do not schedule anything before that time "
            "on the first day. If a departure time is mentioned, do not "
            "schedule anything after that time on the last day. For each "
            "day, use that specific day's weather_code from get_forecast "
            "to decide what to suggest: codes 51-67, 80-82, and 95-99 all "
            "mean rain, drizzle, showers, or a thunderstorm is expected, "
            "so for those days suggest an indoor option or mention "
            "bringing an umbrella, do not suggest an all-outdoor day. "
            "Codes 0-3 are clear to partly cloudy, safe for outdoor plans. "
            "If a day's high temperature is above 32 Celsius, remind the "
            "user to bring sunscreen and a hat, and avoid suggesting a "
            "fully outdoor afternoon in that heat. "
            "A real itinerary must include real meals: call find_places "
            "for restaurant to suggest real meal spots, and if arrival "
            "time is early or mid afternoon, consider that lunch may have "
            "been missed while traveling, and suggest a quick bite. "
            "To keep this affordable, call find_places at most TWICE for "
            "the entire trip, no matter how many days: once for "
            "restaurant, and once for the single activity category that "
            "best fits the destination and weather, beach, attraction, "
            "park, museum, or viewpoint, pick only one. Reuse those same "
            "results across every day of the itinerary instead of "
            "searching again per day. "
            "If, and only if, you already have two or more real activity "
            "options to choose between from that one search, you may call "
            "calculate_distance once or twice to compare real distances "
            "between them, never guess a distance, and never call it if "
            "you only found one real option to begin with. Weigh that "
            "real distance against how notable each place is using your "
            "own general knowledge, labeled honestly as general "
            "reputation, not verified data, and if you do not actually "
            "know anything about a place, say so and lean on distance "
            "instead. Prefer a closer good option over a much farther "
            "excellent one if more stops are planned later that day. "
            "If the user names one specific restaurant or place they want "
            "included, use find_place_by_name to look it up and confirm "
            "it is real, do not just assume it exists or use find_places' "
            "general category results instead. If find_place_by_name "
            "returns nothing, tell the user honestly that you could not "
            "confirm that specific place exists near there. "
            "If you have real day-by-day weather from get_forecast, call "
            "get_outfit_suggestion ONCE, giving it a real plain-English "
            "request describing the actual destination, occasion/vibe, "
            "and weather already gathered. This is a separate real "
            "stylist agent reasoning over the user's actual real "
            "wardrobe, not a guess, so only send it real weather you "
            "already have, never invented conditions. If it honestly "
            "reports a gap, nothing she owns fits, include that gap and "
            "its real shopping suggestion in your final answer instead "
            "of inventing an outfit yourself."
        ) + memory_context,
    }

    # The conversation starts with our system instructions, then the
    # question. Every tool call and every tool result gets added to this
    # same list as we go, so Groq always sees the whole history so far.
    messages = [system_message, {"role": "user", "content": question}]

    refinement_rounds_used = 0

    # Phase 6: real cost tracking. Groq's free tier caps us at 6,000 tokens
    # PER MINUTE, shared across every request. One question chaining several
    # tool calls resends the whole growing conversation each time, so cost
    # adds up fast without us watching it. We track the real running total
    # and stop early, honestly, if a single question gets too expensive,
    # rather than silently eating the whole minute's quota by itself.
    total_tokens_used = 0
    # Raised again, 8000 to 15000 to 18000 to 26000: get_outfit_suggestion
    # is a real, separate agent call, reasoning over dozens of real
    # wardrobe items at once, genuinely more expensive than the old,
    # narrow get_wardrobe_advice it replaced, ~5,000 tokens on its own in
    # a real test run. That run needed 20,274 tokens just to reach a 4/5
    # critic score, with no budget left for the one refinement round it
    # still needed, verified by watching it get cut off right there.
    # Still a real limit, not "no limit", sized with real margin above
    # what a genuinely complete answer, including one refinement round,
    # actually costs right now.
    TOKEN_BUDGET = 26000

    # A hard cap so a bug can never loop forever or burn our free quota.
    # Raised from 8 to 12 here, same reasoning as the token budget above,
    # a real meals-plus-attractions-plus-distance itinerary needs more
    # tool calls than a simple weather-and-restaurants question did.
    for step in range(12):
        print(f"\n--- step {step + 1}: thinking ---")

        # THINK: send the conversation so far, plus the tool list, to Groq.
        # Groq itself sometimes fails to produce a valid tool call, a real,
        # known reliability issue with these models, separate from our own
        # tool failures in phase 4. We retry the call itself up to 3 times
        # before giving up honestly, since this is usually a one-off
        # sampling hiccup that succeeds on a second try.
        response = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                )
                break
            except BadRequestError as error:
                print(f"Groq call failed on attempt {attempt + 1}: {error}")

        if response is None:
            answer = "Sorry, I had trouble reasoning about that question. Please try rephrasing it."
            save_trip(question, answer)
            return answer

        reply = response.choices[0].message

        total_tokens_used += response.usage.total_tokens
        print(f"Tokens this step: {response.usage.total_tokens}, running total: {total_tokens_used}")

        if total_tokens_used > TOKEN_BUDGET:
            print("Token budget exceeded, stopping early.")
            answer = "Sorry, this question needed more resources than I'm allowed to use. Please try asking something more specific."
            save_trip(question, answer)
            return answer

        messages.append(reply)

        # If Groq did not ask for a tool, it decided it has enough to
        # answer. Before trusting that, send it to the critic model, see
        # phase 6.2 notes for why this is a real, separate technique from
        # the "reward points" idea, self-refine, not training.
        if not reply.tool_calls:
            print("Groq decided it has enough to answer, sending to critic.")

            # The critic needs the real data the answer was supposed to be
            # based on, so it can check the answer against real facts, not
            # its own opinion. Every "tool" role message in our
            # conversation so far holds exactly that.
            tool_results_text = "\n".join(
                m["content"] for m in messages if isinstance(m, dict) and m.get("role") == "tool"
            )

            score, feedback, critic_tokens = critique_answer(question, tool_results_text, reply.content)
            total_tokens_used += critic_tokens
            print(f"Critic score: {score}/5, critic tokens: {critic_tokens}, running total: {total_tokens_used}")
            print(f"Critic feedback: {feedback}")

            # The critic's own real cost counts against the same budget,
            # it is real spend, not a free side call, check it the exact
            # same way we check every other step.
            if total_tokens_used > TOKEN_BUDGET:
                print("Token budget exceeded after critic call, stopping early.")
                answer = "Sorry, this question needed more resources than I'm allowed to use. Please try asking something more specific."
                save_trip(question, answer)
                return answer

            if score >= 4 or refinement_rounds_used >= MAX_REFINEMENT_ROUNDS:
                print(f"Total tokens for this question: {total_tokens_used}")
                # Phase 5: save the real question and real answer, so a
                # future run can look back at this instead of zero.
                save_trip(question, reply.content)
                return reply.content

            # Score too low, and we still have a refinement round left.
            # Send the critic's real, specific feedback back to Groq as a
            # new message, and loop back to the top, this consumes one
            # more of the SAME step and token budget, not a fresh one.
            refinement_rounds_used += 1
            print(f"Score too low, refinement round {refinement_rounds_used} of {MAX_REFINEMENT_ROUNDS}.")

            # The real fix from phase 6.2's second bug: don't leave "try
            # again" open-ended. We watched Groq guess wrong twice, missing
            # restaurants meant retrying the SAME failed restaurant search,
            # but it tried a different category instead. If we can see a
            # real tool actually failed, name it directly.
            failed_calls = find_failed_tool_calls(messages)
            if failed_calls:
                failed_list = ", ".join(f"{name}({args})" for name, args in failed_calls)
                retry_instruction = (
                    f"These exact tool calls failed and returned no real "
                    f"data: {failed_list}. If the missing information "
                    f"below is caused by one of these, retry that EXACT "
                    f"SAME tool with the same arguments first, a real "
                    f"server failure is often temporary. Do not switch to "
                    f"a different category or tool instead of retrying."
                )
            else:
                retry_instruction = ""

            # Real safeguard against a wrong critic verdict: a real example
            # of the critic incorrectly claiming a place "was not found"
            # when it genuinely had been, and Groq trusting that wrong
            # claim over its own correct, earlier, successful result. This
            # list is extracted directly from real tool results, not
            # opinion, and Groq is told explicitly to trust it over the
            # reviewer if the two ever disagree.
            real_names = extract_real_place_names(messages)
            if real_names:
                ground_truth = (
                    f"These place names are CONFIRMED REAL, they came "
                    f"directly from a real tool result earlier in this "
                    f"conversation: {', '.join(real_names)}. If the "
                    f"reviewer's feedback claims one of these does not "
                    f"exist or was not found, the reviewer is wrong about "
                    f"that specific point, trust this list instead, do "
                    f"not remove or doubt a real, confirmed place."
                )
            else:
                ground_truth = ""

            messages.append({
                "role": "user",
                "content": (
                    f"A reviewer checked your last answer against the real "
                    f"data and found problems: {feedback}\n"
                    f"{retry_instruction}\n"
                    f"{ground_truth}\n"
                    f"Please give a revised, corrected answer that fixes "
                    f"these specific issues, using the real data already "
                    f"gathered, only call another tool if genuinely needed."
                ),
            })
            continue

        # ACT: Groq can ask for one or more tool calls at once, run each.
        for call in reply.tool_calls:
            tool_name = call.function.name
            tool_args = json.loads(call.function.arguments)
            print(f"Groq asked to call: {tool_name}({tool_args})")

            # Guardrail: block this call entirely, before it ever runs,
            # if it needs real coordinates but geocode_city has not
            # actually succeeded yet. This is a code-level check, not
            # another prompt instruction, because the prompt instruction
            # to "always geocode first" was watched failing live, it is
            # not reliable enough on its own for something this important.
            if tool_name in NEEDS_REAL_COORDS and not has_geocoded_yet(messages):
                result = {
                    "error": "You must call geocode_city first to get "
                             "real coordinates. Do not guess or use "
                             "memorized coordinates yourself."
                }
                print(f"Guardrail blocked {tool_name}: geocode_city has not succeeded yet.")
            else:
                # Phase 4: a tool can genuinely fail, a bad date, a flaky
                # server, a typo in a city name. Before this, any of those
                # crashed the whole agent with no answer at all. Now we catch
                # the failure here, in this one place, and hand Groq a plain
                # description of what went wrong instead. Groq can then decide
                # what to do: retry with different arguments, try a different
                # tool, or tell the user honestly that it couldn't find an
                # answer, the same choices a person would have.
                real_function = AVAILABLE_TOOLS[tool_name]
                try:
                    result = real_function(**tool_args)

                    # get_outfit_suggestion is a real, separate agent
                    # call, same as the critic, its own real cost was
                    # never being counted before this fix, same gap
                    # phase 6.2 found and fixed for critique_answer.
                    # Returns (result, tokens_used), unpack here so the
                    # real cost is added to our own running total, and
                    # only the clean result, never the raw token count,
                    # goes back to Groq as the tool's answer.
                    if tool_name == "get_outfit_suggestion":
                        result, stylist_tokens = result
                        total_tokens_used += stylist_tokens
                        print(f"Stylist agent real cost: {stylist_tokens} tokens, "
                              f"running total: {total_tokens_used}")

                        if total_tokens_used > TOKEN_BUDGET:
                            print("Token budget exceeded after stylist call, stopping early.")
                            answer = "Sorry, this question needed more resources than I'm allowed to use. Please try asking something more specific."
                            save_trip(question, answer)
                            return answer

                    print(f"Real result: {result}")
                except Exception as error:
                    result = {"error": str(error)}
                    print(f"Tool failed: {result}")

            # OBSERVE: send the result back, tagged with which call it
            # answers, so Groq can match it to the right request.
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return "Sorry, I could not find an answer in time."


if __name__ == "__main__":
    # We give explicit dates here on purpose. Groq has no built-in sense of
    # today's date, saying "next weekend" would leave it guessing, that's a
    # real limitation worth knowing about, not something we're hiding.
    question = (
        "I'm visiting Nashville on August 15 and 16, 2026. "
        "What will the weather be like, and where should I eat?"
    )
    answer = run_agent(question)
    print("\n--- final answer ---")
    print(answer)
