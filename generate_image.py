"""
Generates a simple branded quote-card graphic (PNG) for a LinkedIn post.

Usage as a library:
    from generate_image import generate
    generate("Your punchy hook line here", "output.png")

Design: dark navy background, bold centered text, thin accent bar,
small name/tagline footer. Square 1200x1200 (works well on both
desktop and mobile feed).
"""

import json
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 1200
BG_COLOR = (13, 27, 42)        # deep navy
ACCENT_COLOR = (56, 189, 168)  # teal accent
TEXT_COLOR = (240, 244, 248)   # near-white
FOOTER_COLOR = (140, 160, 175)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(SCRIPT_DIR, "fonts", "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(SCRIPT_DIR, "fonts", "DejaVuSans.ttf")

DEFAULT_NAME = "Your Name"
DEFAULT_TAGLINE = "Your tagline here"


def _load_branding():
    """Reads display_name/tagline from config.json, falling back to
    generic placeholders if the file or the keys are missing."""
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
        return (
            config.get("display_name") or DEFAULT_NAME,
            config.get("tagline") or DEFAULT_TAGLINE,
        )
    return DEFAULT_NAME, DEFAULT_TAGLINE


def _fit_font_size(draw, text, font_path, max_width, max_height, start_size=72, min_size=32):
    """Shrinks font size until wrapped text fits within max_width/max_height."""
    size = start_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        avg_char_width = font.getlength("x") or 1
        wrap_width = max(10, int(max_width / avg_char_width))
        lines = textwrap.wrap(text, width=wrap_width)
        line_height = font.getbbox("Ag")[3] + 14
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, lines, line_height
        size -= 4
    font = ImageFont.truetype(font_path, min_size)
    lines = textwrap.wrap(text, width=max(10, int(max_width / (font.getlength("x") or 1))))
    line_height = font.getbbox("Ag")[3] + 14
    return font, lines, line_height


def generate(text: str, output_path: str = "post_image.png"):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Accent bar top-left
    draw.rectangle([(80, 90), (170, 98)], fill=ACCENT_COLOR)

    # Main quote text, auto-sized to fit
    max_text_width = WIDTH - 160
    max_text_height = 700
    font, lines, line_height = _fit_font_size(
        draw, text, FONT_BOLD, max_text_width, max_text_height
    )

    total_text_height = line_height * len(lines)
    y = (HEIGHT - total_text_height) // 2 - 40
    for line in lines:
        line_width = draw.textlength(line, font=font)
        x = (WIDTH - line_width) // 2
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)
        y += line_height

    # Footer: name + tagline
    name, tagline = _load_branding()
    footer_font = ImageFont.truetype(FONT_BOLD, 30)
    tagline_font = ImageFont.truetype(FONT_REGULAR, 24)

    draw.rectangle([(80, HEIGHT - 140), (170, HEIGHT - 132)], fill=ACCENT_COLOR)
    draw.text((80, HEIGHT - 120), name, font=footer_font, fill=TEXT_COLOR)
    draw.text((80, HEIGHT - 80), tagline, font=tagline_font, fill=FOOTER_COLOR)

    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else "Sample quote card text for testing layout."
    path = generate(text)
    print(f"Saved to {path}")
