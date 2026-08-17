"""
llm_utils.py -- phase 7.5/7 handoff: real, shared fixes, started as
vision-only (wardrobe_vision.py, inspiration_vision.py, real oversized
photos and fragile JSON parsing), extended once stylist.py hit the
exact same JSON-parsing bug from a completely different model, proof
this is a general "models don't always return clean JSON" problem, not
a vision-model quirk.
"""
import base64
import io
import json

from PIL import Image

# Real bug hit live: IMG_2967.PNG, an 8.3MB real photo, got rejected by
# Groq with a real 413 "Request Entity Too Large". Resizing to a real,
# sensible max dimension before sending fixes this for any photo this
# large or larger, not just the one that happened to fail first.
MAX_DIMENSION = 1568


def encode_image_for_vision(photo_path):
    """Read a real image file, resize it if it's larger than a vision
    model actually needs, and return a base64 JPEG data URL. Always
    re-encodes as JPEG, regardless of the real original format, so the
    mime type is never a guess."""
    image = Image.open(photo_path)
    image = image.convert("RGB")

    width, height = image.size
    if max(width, height) > MAX_DIMENSION:
        scale = MAX_DIMENSION / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def extract_json(raw_text, fallback_key):
    """Real bug hit live: IMG_2652.PNG's real response had extra text
    around the real JSON, our old check (only strips a fence at the very
    start) missed it, and the ENTIRE raw response, including the real
    source_brand/source_product_name the model did correctly extract,
    got shoved into a single fallback field, losing real structured
    data. This finds the first '{' and the last '}' and parses only
    that real substring, which survives a leading sentence, a trailing
    fence, or both, instead of requiring the response to start and end
    exactly right. fallback_key is which key gets the raw text if even
    this can't find valid JSON, an honest, visible failure, never a
    silent guess."""
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw_text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {fallback_key: raw_text}
