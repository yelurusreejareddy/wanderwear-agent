"""
wardrobe_vision.py -- phase 7: look at a real photo of a real clothing
item and draft a first-pass label for it. This is a DRAFT only, never
treated as fact. Only Sreeja actually knows if something is "date night"
or "casual", the model is just giving us a starting guess so she is
correcting labels instead of typing all of them from a blank page.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

from llm_utils import encode_image_for_vision, extract_json

load_dotenv()

client = OpenAI(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_BASE_URL"))

# The only vision-capable model on Groq's free tier, confirmed on their own
# docs: console.groq.com/docs/vision and console.groq.com/docs/rate-limits.
# Free tier real limits: 30 requests/min, 1000 requests/day, 200,000
# tokens/day, plenty for a one-time tagging pass over a real wardrobe.
VISION_MODEL = "qwen/qwen3.6-27b"

SYSTEM_PROMPT = (
    "You are looking at one real photo of one real clothing item, either "
    "laid flat, on a hanger, or worn by the owner in a mirror. Describe "
    "ONLY what you can actually see in this photo. Reply with JSON only, "
    "no other text, in exactly this shape: "
    '{"category": "top/dress/pants/jacket/skirt/etc", '
    '"color": "the real color you see", '
    '"style_notes": "a short real description, ribbed, cropped, floral, '
    'off-shoulder, etc"}. '
    "If a person is wearing the item, describe the clothing, not the "
    "person. If you cannot tell something, say \"unclear\", never guess "
    "or invent a detail you cannot actually see."
)


def draft_label(photo_path):
    """Send one real photo to the vision model, get back a draft
    category/color/style_notes dict. Returns the dict plus real token
    cost, same (result, tokens_used) shape as the other tool functions,
    so loop.py can count this cost the same way."""
    image_data_url = encode_image_for_vision(photo_path)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this real clothing item?"},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        # Real, confirmed fix: without this, qwen3.6 defaults to a long
        # "thinking out loud" block before its real answer, which is not
        # valid JSON and burns 5-10x the real tokens for no real benefit
        # here, we just need the final label, not the model's reasoning.
        # "none" is a real documented value on Groq's own reasoning docs,
        # specific to this model.
        reasoning_effort="none",
    )

    raw_text = response.choices[0].message.content.strip()
    tokens_used = response.usage.total_tokens

    label = extract_json(raw_text, fallback_key="style_notes")
    label.setdefault("category", "unclear")
    label.setdefault("color", "unclear")

    return label, tokens_used


if __name__ == "__main__":
    # Real test: 3 real photos from the actual closet folder, picked to
    # cover both photo styles in there, flat/hanger shots and a worn shot.
    closet_dir = "/Users/boo/Documents/personal-agent/closet"
    test_files = [
        "IMG_9D4B0497-41A5-4A4A-A671-C30F39D44B27.jpeg",
        "IMG_5B059CAA-053E-4CEA-AB07-F6FB78048E00.jpeg",
        "IMG_1419.jpeg",
    ]

    total_tokens = 0
    for file_name in test_files:
        full_path = os.path.join(closet_dir, file_name)
        label, tokens = draft_label(full_path)
        total_tokens += tokens
        print(f"\n{file_name}")
        print(f"  category: {label.get('category')}")
        print(f"  color: {label.get('color')}")
        print(f"  style_notes: {label.get('style_notes')}")

    print(f"\nreal total cost: {total_tokens} tokens")
