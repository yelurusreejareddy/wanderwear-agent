"""
loop_langgraph.py -- phase 8: the exact same real agent as loop.py,
rebuilt on LangGraph instead of a hand-written for loop.

Nothing "smart" changes here. Every real tool, every real guardrail,
the critic, all imported directly from loop.py, not copied, so this
file can never quietly drift into a second, different version of logic
that took real bugs to get right. The only thing this file adds is the
graph wiring: naming the steps as nodes, and naming the decisions as
edges, exactly the shape shown in the diagrams earlier.

loop.py is left completely untouched, on purpose, so it stays a real,
working, side-by-side reference for comparing the two.

One real, honest piece of duplication: the long system message text
below is copied from loop.py's run_agent, not imported, because
loop.py builds it as a local variable inside that function, it was
never exported as its own reusable piece. Everything else here is a
real import, not a copy.
"""
import datetime
import json
import operator
from typing import Annotated, TypedDict

from openai import BadRequestError
from langgraph.graph import StateGraph, START, END
from langgraph.errors import GraphRecursionError

from loop import (
    client, MODEL, TOOLS, AVAILABLE_TOOLS, NEEDS_REAL_COORDS,
    MAX_REFINEMENT_ROUNDS, critique_answer, find_failed_tool_calls,
    extract_real_place_names, has_geocoded_yet,
)
from memory import get_recent_trips, save_trip

# Real, honest duplication, same reason as the system message text
# below: TOKEN_BUDGET lives INSIDE loop.py's run_agent function, a
# local variable, not a module-level constant, so there is nothing to
# import here. Copied, not re-derived, keep this in sync with loop.py
# by hand if that real number ever changes there again.
#
# Raised again, 26000 to 35000, real evidence via the real API: a
# genuinely thorough real question, Groq searching BOTH restaurants
# and museums, comparing real distances between two museum options,
# AND calling the stylist agent, all in one run, cost 28,767 tokens,
# confirmed by reading the real per-step log, not guessed. This real
# number only shows up when Groq chooses to do this much real research
# in one question, loop.py's own copy of this same real constant may
# need the identical raise if a question that thorough ever hits it
# too, not touched here since loop.py is left alone on purpose.
TOKEN_BUDGET = 35000


# The State: what flows through the graph. Every node reads this and
# returns updates to it. "messages" uses operator.add as its real
# reducer, meaning a node returning {"messages": [x]} means "add this
# one new item", the exact same meaning as loop.py's messages.append(x),
# just declared once here instead of written out at every call site.
class AgentState(TypedDict):
    question: str
    messages: Annotated[list, operator.add]
    total_tokens_used: int
    refinement_rounds_used: int
    needs_revision: bool
    over_budget: bool


def call_model_node(state):
    """The 'think' node. Real, direct equivalent of the top of loop.py's
    for-loop: ask Groq what to do next, given the real conversation so
    far. Same 3-attempt retry, same real reason, Groq occasionally fails
    to produce a valid tool call, a known reliability issue."""
    response = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL, messages=state["messages"], tools=TOOLS,
            )
            break
        except BadRequestError as error:
            print(f"Groq call failed on attempt {attempt + 1}: {error}")

    if response is None:
        apology = {
            "role": "assistant",
            "content": "Sorry, I had trouble reasoning about that question. Please try rephrasing it.",
        }
        return {"messages": [apology], "over_budget": True}

    reply = response.choices[0].message
    new_total = state["total_tokens_used"] + response.usage.total_tokens
    print(f"Tokens this step: {response.usage.total_tokens}, running total: {new_total}")

    if new_total > TOKEN_BUDGET:
        print("Token budget exceeded, stopping early.")
        apology = {
            "role": "assistant",
            "content": "Sorry, this question needed more resources than I'm allowed to use. Please try asking something more specific.",
        }
        return {"messages": [reply, apology], "total_tokens_used": new_total, "over_budget": True}

    return {"messages": [reply], "total_tokens_used": new_total}


def route_after_model(state):
    """The first conditional edge. Real, direct equivalent of loop.py's
    `if not reply.tool_calls:` check, just pulled out as its own named
    function instead of an if/else inline in the loop."""
    if state.get("over_budget"):
        return END
    if state["messages"][-1].tool_calls:
        return "tools"
    return "critique"


def tools_node(state):
    """The 'act' node. Real, direct equivalent of loop.py's
    `for call in reply.tool_calls:` block, same guardrail, same
    exception handling, same stylist-cost unpacking, none of that logic
    changed, it just lives in a function named tools_node now."""
    reply = state["messages"][-1]
    total = state["total_tokens_used"]
    over_budget = False
    new_messages = []

    for call in reply.tool_calls:
        tool_name = call.function.name
        tool_args = json.loads(call.function.arguments)
        print(f"Groq asked to call: {tool_name}({tool_args})")

        if tool_name in NEEDS_REAL_COORDS and not has_geocoded_yet(state["messages"]):
            result = {
                "error": "You must call geocode_city first to get real "
                         "coordinates. Do not guess or use memorized "
                         "coordinates yourself."
            }
            print(f"Guardrail blocked {tool_name}: geocode_city has not succeeded yet.")
        else:
            real_function = AVAILABLE_TOOLS[tool_name]
            try:
                result = real_function(**tool_args)

                if tool_name == "get_outfit_suggestion":
                    result, stylist_tokens = result
                    total += stylist_tokens
                    print(f"Stylist agent real cost: {stylist_tokens} tokens, running total: {total}")
                    if total > TOKEN_BUDGET:
                        over_budget = True

                print(f"Real result: {result}")
            except Exception as error:
                result = {"error": str(error)}
                print(f"Tool failed: {result}")

        new_messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(result),
        })

    if over_budget:
        print("Token budget exceeded after stylist call, stopping early.")
        new_messages.append({
            "role": "assistant",
            "content": "Sorry, this question needed more resources than I'm allowed to use. Please try asking something more specific.",
        })

    return {"messages": new_messages, "total_tokens_used": total, "over_budget": over_budget}


def route_after_tools(state):
    """Real equivalent of the bottom of loop.py's for-loop simply going
    around again after running a tool, always back to thinking, unless
    the stylist call itself pushed us over budget."""
    if state.get("over_budget"):
        return END
    return "call_model"


def critique_node(state):
    """The self-refine node. Real, direct equivalent of loop.py's
    critic block: score the answer, check the real budget, and either
    accept it or build the exact same revision message, with the same
    two real guardrails (find_failed_tool_calls, extract_real_place_names)
    protecting against the critic's own known failure modes."""
    reply = state["messages"][-1]
    tool_results_text = "\n".join(
        m["content"] for m in state["messages"] if isinstance(m, dict) and m.get("role") == "tool"
    )

    score, feedback, critic_tokens = critique_answer(state["question"], tool_results_text, reply.content)
    total = state["total_tokens_used"] + critic_tokens
    print(f"Critic score: {score}/5, critic tokens: {critic_tokens}, running total: {total}")
    print(f"Critic feedback: {feedback}")

    if total > TOKEN_BUDGET:
        print("Token budget exceeded after critic call, stopping early.")
        apology = {
            "role": "assistant",
            "content": "Sorry, this question needed more resources than I'm allowed to use. Please try asking something more specific.",
        }
        return {"messages": [apology], "total_tokens_used": total, "over_budget": True, "needs_revision": False}

    rounds_used = state["refinement_rounds_used"]
    if score >= 4 or rounds_used >= MAX_REFINEMENT_ROUNDS:
        print(f"Total tokens for this question: {total}")
        return {"total_tokens_used": total, "needs_revision": False}

    rounds_used += 1
    print(f"Score too low, refinement round {rounds_used} of {MAX_REFINEMENT_ROUNDS}.")

    failed_calls = find_failed_tool_calls(state["messages"])
    if failed_calls:
        failed_list = ", ".join(f"{name}({args})" for name, args in failed_calls)
        retry_instruction = (
            f"These exact tool calls failed and returned no real data: "
            f"{failed_list}. If the missing information below is caused "
            f"by one of these, retry that EXACT SAME tool with the same "
            f"arguments first, a real server failure is often temporary. "
            f"Do not switch to a different category or tool instead of retrying."
        )
    else:
        retry_instruction = ""

    real_names = extract_real_place_names(state["messages"])
    if real_names:
        ground_truth = (
            f"These place names are CONFIRMED REAL, they came directly "
            f"from a real tool result earlier in this conversation: "
            f"{', '.join(real_names)}. If the reviewer's feedback claims "
            f"one of these does not exist or was not found, the reviewer "
            f"is wrong about that specific point, trust this list "
            f"instead, do not remove or doubt a real, confirmed place."
        )
    else:
        ground_truth = ""

    revision_message = {
        "role": "user",
        "content": (
            f"A reviewer checked your last answer against the real data "
            f"and found problems: {feedback}\n{retry_instruction}\n{ground_truth}\n"
            f"Please give a revised, corrected answer that fixes these "
            f"specific issues, using the real data already gathered, "
            f"only call another tool if genuinely needed."
        ),
    }

    return {
        "messages": [revision_message],
        "total_tokens_used": total,
        "refinement_rounds_used": rounds_used,
        "needs_revision": True,
    }


def route_after_critique(state):
    """Real equivalent of loop.py's `if score >= 4 or rounds_used >=
    MAX: return` versus `continue` decision."""
    if state.get("over_budget"):
        return END
    if state.get("needs_revision"):
        return "call_model"
    return END


# The graph itself: name every node, wire every edge. This is the part
# with no equivalent in loop.py, there was nothing to "build" before,
# the shape only existed implicitly in how the for-loop happened to
# behave. Here it's a real object.
graph_builder = StateGraph(AgentState)
graph_builder.add_node("call_model", call_model_node)
graph_builder.add_node("tools", tools_node)
graph_builder.add_node("critique", critique_node)

graph_builder.add_edge(START, "call_model")
graph_builder.add_conditional_edges(
    "call_model", route_after_model, {"tools": "tools", "critique": "critique", END: END},
)
graph_builder.add_conditional_edges(
    "tools", route_after_tools, {"call_model": "call_model", END: END},
)
graph_builder.add_conditional_edges(
    "critique", route_after_critique, {"call_model": "call_model", END: END},
)

graph = graph_builder.compile()


def run_agent(question):
    """Same real job as loop.py's run_agent(question): build the real
    system message, run the agent, save and return the real answer.
    Real, honest simplification LangGraph gives us here: loop.py has
    FOUR separate places that call save_trip, one per early-return path.
    Every path through the graph converges back to one place, here,
    so there is only one, impossible to forget on a path we didn't
    think of."""
    today = datetime.date.today().isoformat()

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

    initial_state = {
        "question": question,
        "messages": [system_message, {"role": "user", "content": question}],
        "total_tokens_used": 0,
        "refinement_rounds_used": 0,
        "needs_revision": False,
        "over_budget": False,
    }

    # Real, honest bug found on the first genuinely long real trip
    # question run through the API: LangGraph's recursion_limit counts
    # EVERY node visit, not "rounds" the way loop.py's `for step in
    # range(12):` counted them. Our graph spends 2 node visits per real
    # round, call_model then tools, so a limit of 12 only ever allowed
    # 6 real rounds, half of loop.py's real capacity, confirmed live: a
    # real 6-tool-call trip question got cut off exactly at the 12th
    # node visit. Doubled to give the same real capacity as loop.py's cap.
    try:
        final_state = graph.invoke(initial_state, config={"recursion_limit": 24})
    except GraphRecursionError:
        print("Recursion limit hit, stopping honestly instead of failing silently.")
        # Real equivalent of loop.py's `for step in range(12):` finishing
        # without ever returning, the same honest "ran out of steps"
        # fallback, just raised as a real exception here instead of a
        # loop quietly finishing.
        answer = "Sorry, I could not find an answer in time."
        save_trip(question, answer)
        return answer

    last_message = final_state["messages"][-1]
    answer = last_message.content if hasattr(last_message, "content") else last_message["content"]
    save_trip(question, answer)
    return answer


if __name__ == "__main__":
    question = (
        "I'm visiting Nashville on August 15 and 16, 2026. "
        "What will the weather be like, and where should I eat?"
    )
    answer = run_agent(question)
    print("\n--- final answer ---")
    print(answer)
