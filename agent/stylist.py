"""
stylist.py -- phase 7: the real stylist agent. Reasons over Sreeja's
actual real wardrobe, stored in Supabase, and suggests a real outfit for
a real request (place, vibe, mood, weather). Occasion is NOT a fixed
label stored per item, it's reasoned live from the real combination
chosen, the same top can be casual or date-night depending what it's
paired with, exactly what she asked for.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

from auth_context import get_client
from llm_utils import extract_json
from photo_access import sign_photo_url

load_dotenv()

client = OpenAI(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_BASE_URL"))

# The main model, not the smaller critic/vision ones, real outfit
# reasoning over dozens of real items at once is a genuine primary task,
# the same reason the travel agent itself uses the main model.
STYLIST_MODEL = os.getenv("LLM_MODEL")

SYSTEM_PROMPT = (
    "You are a real personal stylist. You will be given two real lists "
    "and a real request describing place, vibe, mood, or weather. "
    "List 1, real owned wardrobe: items the user actually owns, each "
    "with a real id, category, color, and style notes. List 2, real "
    "saved style inspiration: outfits she saved from other people, "
    "influencers, or shopping sites because she liked the look, each "
    "with a real id, description, and sometimes a real brand/product "
    "name. She does NOT own anything in list 2, it exists only so you "
    "can recall a look she liked and compare it against what she "
    "actually owns. NEVER put a list 2 id anywhere near outfit_item_ids, "
    "that field is real owned items only, list 2 ids never go there. "
    "Pick a real, complete outfit using ONLY real owned items, "
    "referenced by their real id, never invent an item that is not in "
    "list 1. Reason about the occasion from the SPECIFIC COMBINATION "
    "you choose, not any single item's fixed identity, the exact same "
    "top can read casual or date-night depending what it is paired "
    "with, that judgment is your real job. "
    "If a real saved inspiration look genuinely matches the request's "
    "vibe, you may reference it by id in inspiration_reference_id, and "
    "if her real wardrobe can recreate that same vibe with owned items, "
    "say so in your reasoning. If a previous suggestion for this same "
    "request was rejected, pick a genuinely different real combination, "
    "do not repeat rejected items. "
    "If nothing in her real wardrobe actually fits the request well, say "
    "so honestly instead of forcing a bad combination, set fits_request "
    "to false, and add a real gap_note plus a shopping_suggestion. If a "
    "real inspiration entry matches the request AND has a real "
    "source_brand/source_product_name, use that exact real product as "
    "the shopping_suggestion instead of inventing one, and set "
    "inspiration_reference_id to its real id. Only fall back to general "
    "fashion knowledge, clearly your own general knowledge, not "
    "anything drawn from her actual data, when no matching real "
    "inspiration entry with real source info exists. "
    "If the request names a specific, checkable requirement, a length "
    "(floor-length, maxi), a fabric, a formality level, and the wardrobe "
    "data does not EXPLICITLY confirm that exact requirement, do not "
    "assume or round up to it. A 'high-low hemline' is NOT the same "
    "thing as floor-length, a midi is NOT the same thing as a maxi, "
    "treat an unconfirmed exact match as a real gap, fits_request "
    "false, rather than stretching a real item's real description to "
    "fit the request. "
    "Reply with JSON only, no other text, in exactly this shape: "
    '{"outfit_item_ids": [1, 2], "reasoning": "why this combination '
    'fits the request", "fits_request": true, "gap_note": null, '
    '"shopping_suggestion": null, "inspiration_reference_id": null}'
)


def _get_full_wardrobe():
    """Every real item currently in the real wardrobe_items table,
    RLS (phase 12) already limits this to the real, current user's
    own rows."""
    response = get_client().table("wardrobe_items").select("*").execute()
    return response.data


def _get_full_inspiration():
    """Every real saved style photo currently in style_inspiration,
    same real per-user limit as _get_full_wardrobe."""
    response = get_client().table("style_inspiration").select("*").execute()
    return response.data


def _format_wardrobe_for_prompt(items):
    """A compact real listing, id/category/color/style_notes only, real
    photo URLs are left out here since the model never needs to see a
    URL to reason about the item, keeping this cheap in real tokens."""
    lines = []
    for item in items:
        lines.append(
            f"id {item['id']}: {item['category']}, {item['color']}, "
            f"{item['style_notes']}"
        )
    return "\n".join(lines)


def _format_inspiration_for_prompt(items):
    """Same idea as the wardrobe listing, id/description, plus real
    source info only when it actually exists, never filled in as a
    guess."""
    lines = []
    for item in items:
        line = f"id {item['id']}: {item['description']}"
        if item.get("source_brand"):
            line += f" (real source: {item['source_brand']} - {item.get('source_product_name')})"
        lines.append(line)
    return "\n".join(lines)


def suggest_outfit(request, rejected_ids=None):
    """Ask the real stylist agent for a real outfit from the real
    wardrobe, informed by real saved style inspiration. rejected_ids, if
    given, are real item ids from a previous suggestion for this same
    request that Sreeja said she didn't like. Returns (result_dict,
    real_items_chosen, real_inspiration_referenced, tokens_used)."""
    wardrobe = _get_full_wardrobe()
    inspiration = _get_full_inspiration()
    wardrobe_text = _format_wardrobe_for_prompt(wardrobe)
    inspiration_text = _format_inspiration_for_prompt(inspiration)

    user_content = (
        f"Real owned wardrobe:\n{wardrobe_text}\n\n"
        f"Real saved style inspiration (NOT owned):\n{inspiration_text}\n\n"
        f"Request: {request}"
    )
    if rejected_ids:
        user_content += (
            f"\n\nAlready rejected real item ids for this same request, "
            f"do not reuse them: {rejected_ids}"
        )

    response = client.chat.completions.create(
        model=STYLIST_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    tokens_used = response.usage.total_tokens

    # Real bug hit live wiring this into loop.py: this model (the MAIN
    # model, gpt-oss-120b, not the vision one) has the exact same real
    # habit of surrounding its JSON with extra text, proof this is a
    # general "models don't always return clean JSON" problem, not a
    # vision-model quirk. Same real fix already proven twice there.
    result = extract_json(raw_text, fallback_key="reasoning")

    # Real guardrail, same idea as has_geocoded_yet in loop.py: never
    # trust the model's own claim about which real items it picked,
    # look them up for real so a hallucinated id can't silently reach
    # the user as if it were a real piece of her wardrobe.
    wardrobe_by_id = {item["id"]: item for item in wardrobe}
    real_items_chosen = []
    for item_id in result.get("outfit_item_ids", []):
        real_item = wardrobe_by_id.get(item_id)
        if real_item is not None:
            real_items_chosen.append(real_item)

    # Same real guardrail applied to the inspiration reference: only a
    # real, existing style_inspiration id is ever handed back, a
    # hallucinated one is silently dropped rather than shown as real.
    inspiration_by_id = {item["id"]: item for item in inspiration}
    real_inspiration_referenced = inspiration_by_id.get(result.get("inspiration_reference_id"))

    return result, real_items_chosen, real_inspiration_referenced, tokens_used


def get_outfit_suggestion_for_trip(request, rejected_ids=None):
    """Real handoff entry point for loop.py AND the real FastAPI
    /style-me endpoint (phase 9): the travel agent calls this once it
    has real trip context (place, weather, vibe), same as the old,
    narrower get_wardrobe_advice used to be called. rejected_ids, added
    for the API's real feedback loop, forwards straight to
    suggest_outfit unchanged. Returns (clean_result, tokens_used), a
    plain 2-tuple, so a caller can count the real cost without seeing
    internal real ids as if they were part of the answer, except each
    outfit item's own real id IS included here, unlike the older
    internal use, because the API's real feedback loop needs a real id
    to send back as a future rejected_ids entry."""
    result, items, inspiration, tokens = suggest_outfit(request, rejected_ids)

    # Real, deliberate choice: sign every photo URL right here, at the
    # one real exit point every caller (loop.py, the API, the REPL)
    # goes through, rather than in each caller separately. The stored
    # photo_url is the old, now-private-and-broken permanent link,
    # this swaps in a real, temporary one, good for the real 1-hour
    # window defined in photo_access.py, never a stale dead link.
    clean_result = {
        "fits_request": result.get("fits_request"),
        "reasoning": result.get("reasoning"),
        "gap_note": result.get("gap_note"),
        "shopping_suggestion": result.get("shopping_suggestion"),
        "outfit": [
            {
                "id": item["id"],
                "category": item["category"],
                "color": item["color"],
                "style_notes": item["style_notes"],
                "photo_url": sign_photo_url(item["photo_url"]),
            }
            for item in items
        ],
    }
    if inspiration:
        clean_result["inspired_by_saved_look"] = {
            "description": inspiration["description"],
            "photo_url": sign_photo_url(inspiration["photo_url"]),
            "product_url": inspiration.get("product_url"),
        }

    return clean_result, tokens


def _print_suggestion(result, items, inspiration_referenced):
    # Same real reason as get_outfit_suggestion_for_trip: the REPL
    # calls suggest_outfit directly, not through that wrapper, so it
    # needs its own real sign_photo_url call here, otherwise this
    # would print the old, now-private, dead links instead.
    if result.get("fits_request"):
        print("\nHere's what I'd suggest:")
        print(f"  {result.get('reasoning')}\n")
        for item in items:
            print(f"  - {item['category']}, {item['color']}, {item['style_notes']}")
            print(f"    {sign_photo_url(item['photo_url'])}")
    else:
        print(f"\nHonest gap: {result.get('gap_note')}")
        print(f"What to consider buying: {result.get('shopping_suggestion')}")

    if inspiration_referenced:
        print(f"\n  (inspired by a real saved look: {inspiration_referenced['description']})")
        print(f"   {sign_photo_url(inspiration_referenced['photo_url'])}")
        if inspiration_referenced.get("product_url"):
            print(f"   real buy link: {inspiration_referenced['product_url']}")


def run_stylist_repl():
    """A real, live conversation with the stylist agent. Ask for an
    outfit, say 'no' to get a genuinely different real combination for
    the exact same request, or type a new request to start over."""
    print("Tell me the place/vibe/mood/weather, and I'll suggest a real "
          "outfit from your actual wardrobe. Say 'no' if you don't like "
          "a suggestion, or ask something new any time. Ctrl+C to quit.")

    current_request = None
    rejected_ids = []
    total_tokens = 0

    while True:
        user_input = input("\n> ").strip()
        if not user_input:
            continue

        if user_input.lower() in ("no", "n", "i don't like it", "another"):
            if current_request is None:
                print("Ask me for an outfit first.")
                continue
        else:
            current_request = user_input
            rejected_ids = []

        result, items, inspiration_referenced, tokens = suggest_outfit(current_request, rejected_ids)
        total_tokens += tokens
        rejected_ids.extend(item["id"] for item in items)
        _print_suggestion(result, items, inspiration_referenced)
        print(f"\n(real cost so far this session: {total_tokens} tokens)")


if __name__ == "__main__":
    run_stylist_repl()
