"""Render text as an image and send it to the e-paper display."""

from __future__ import annotations

import importlib
import os
import sys
import textwrap
import time
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

import util

FONT_DIR = util.ROOT / "font"
DEBUG_DIR = util.VAR_DIR / "debug"
FOOTER_FONT = "Font.ttc"
LINE_SPACING = 1.4
# Share of the display height one line may take when deciding whether the text fits
LINE_BUDGET = 1.5


@dataclass(frozen=True)
class Settings:
    max_font: int
    font_steps: int
    dot_size: int
    margin: int


SETTINGS = {
    "epd2in13": Settings(max_font=36, font_steps=2, dot_size=2, margin=2),
    "epd7in5": Settings(max_font=92, font_steps=4, dot_size=4, margin=10),
}

_epd = None
_settings: Settings | None = None


def init() -> None:
    global _epd, _settings

    name = os.environ.get("CLOCKWORK_DISPLAY")
    if name not in SETTINGS:
        sys.exit(f"[error] Not supported display: {name}")

    _epd = importlib.import_module(f"epd.{name}").init()
    _settings = SETTINGS[name]


def _device():
    if _epd is None:
        init()
    return _epd


def size() -> tuple[int, int]:
    """Width and height in landscape orientation."""
    epd = _device()
    return max(epd.width, epd.height), min(epd.width, epd.height)


@lru_cache(maxsize=None)
def font(name: str, font_size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), font_size)


def fit_text(text: str, width: int, height: int, font_size: int):
    """Shrink the font until the wrapped text fits. Returns font, lines and line height."""
    font_name = os.environ.get("CLOCKWORK_FONT")
    while True:
        current = font(font_name, font_size)
        widths = [current.getbbox(char)[2] for char in text]
        max_chars = int(width / (sum(widths) / len(text)) * .9)
        # The widest glyph serves as line height. Odd, but the layout is tuned to it.
        line_height = max(widths)
        lines = [line for part in text.splitlines() for line in textwrap.wrap(part, width=max_chars)]

        if len(lines) <= int(height / (line_height * LINE_BUDGET)) or font_size <= _settings.font_steps:
            return current, lines, line_height
        font_size -= _settings.font_steps


def draw_text(text: str, additional_text=False, additional_hint: bool = False) -> None:
    width, height = size()
    margin = _settings.margin
    image = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(image)

    text_font, lines, line_height = fit_text(text, width, height, _settings.max_font)
    y = margin
    for line in lines:
        draw.text((margin, y), line, font=text_font, fill=0)
        y += line_height * LINE_SPACING

    if additional_text:
        draw.text((width, height), str(additional_text), font=font(FOOTER_FONT, 10), fill=0, align="right", anchor="rb")

    if additional_hint and util.env_bool("CLOCKWORK_DEBUG"):
        # Visual hint that a stored poem is shown
        dot = _settings.dot_size
        draw.ellipse([(width - margin - dot, margin), (width - margin, margin + dot)], fill=0)

    print(f"[draw] {text}")
    display(image, "draw_text")


def intro() -> None:
    width, height = size()
    image = Image.new("1", (width, height), 255)
    draw = ImageDraw.Draw(image)
    draw.text((52, 45), "clockwork/ai", font=font(FOOTER_FONT, 24), fill=0)

    draw.line([(39, 80), (110, 80)], fill=0, width=2)
    draw.line([(44, 85), (80, 85)], fill=0, width=2)
    draw.line([(39, 80), (39, 60)], fill=0, width=2)

    draw.line([(199, 40), (150, 40)], fill=0, width=2)
    draw.line([(199, 40), (199, 60)], fill=0, width=2)
    display(image, "intro")

    time.sleep(2)


def display(image: Image.Image, name: str) -> None:
    """Show the image on the display, or save it under var/debug in dry run mode."""
    epd = _device()
    image = image.rotate(util.env_int("CLOCKWORK_ROTATE", 0))
    if util.DRY_RUN:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        image.save(DEBUG_DIR / f"{name}.jpg")
    else:
        epd.display(epd.getbuffer(image))


def clear() -> None:
    if util.DRY_RUN:
        return

    print("[info] Clear display")
    epd = _device()
    epd.init()
    epd.Clear()
    epd.sleep()
