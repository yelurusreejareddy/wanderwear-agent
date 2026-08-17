"""
inspiration_vision.py -- phase 7.5: look at a real saved style photo,
an influencer's outfit post, a personal photo of someone else's outfit,
a shopping-site screenshot, and draft a real description. This is a
style Sreeja liked and saved, NEVER an item she owns, the stylist agent
must only ever use this to recall a look or suggest what to buy, never
to reason as if it were part of her real wardrobe.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

from llm_utils import encode_image_for_vision, extract_json

load_dotenv()

client = OpenAI(api_key=os.getenv("LLM_API_KEY"), base_url=os.getenv("LLM_BASE_URL"))

VISION_MODEL = "qwen/qwen3.6-27b"

SYSTEM_PROMPT = (
    "You are looking at one real saved photo of a styled outfit, on "
    "another person, an influencer's social media post, a personal "
    "photo, or a real shopping website screenshot. This is NOT clothing "
    "the user owns, it is a style she saved because she liked it. "
    "Describe ONLY what you can actually see. Reply with JSON only, no "
    "other text, in exactly this shape: "
    '{"description": "a real, short description of the outfit and '
    'styling shown, garment types, colors, how it is styled together", '
    '"source_brand": "a real brand name ONLY if actually visible in the '
    'photo, like a website logo or name, otherwise null", '
    '"source_product_name": "a real product name ONLY if actually '
    'visible in the photo, like a product title on a shopping page, '
    'otherwise null"}. '
    "Never invent a brand or product name that is not actually visible "
    "in the photo, if this is an Instagram post or personal photo with "
    "no shopping information, both source fields must be null."
)


def draft_inspiration_label(photo_path):
    """Send one real inspiration photo to the vision model, get back a
    draft description plus real brand/product name when actually
    visible. Returns (label_dict, tokens_used)."""
    image_data_url = encode_image_for_vision(photo_path)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this real saved style photo."},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        reasoning_effort="none",
    )

    raw_text = response.choices[0].message.content.strip()
    tokens_used = response.usage.total_tokens

    label = extract_json(raw_text, fallback_key="description")
    label.setdefault("source_brand", None)
    label.setdefault("source_product_name", None)

    return label, tokens_used


if __name__ == "__main__":
    inspos_dir = "/Users/boo/Documents/personal-agent/closet/inspos"
    test_files = ["IMG_2275.PNG", "IMG_2923.jpeg", "IMG_3142.PNG"]

    total_tokens = 0
    for file_name in test_files:
        full_path = os.path.join(inspos_dir, file_name)
        label, tokens = draft_inspiration_label(full_path)
        total_tokens += tokens
        print(f"\n{file_name}")
        print(f"  description: {label.get('description')}")
        print(f"  source_brand: {label.get('source_brand')}")
        print(f"  source_product_name: {label.get('source_product_name')}")

    print(f"\nreal total cost: {total_tokens} tokens")
