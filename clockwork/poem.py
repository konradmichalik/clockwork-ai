"""Choose or generate the poem for the current time."""

from __future__ import annotations

import logging
import os
import random
import sys
import time
from datetime import datetime

import display
import fs
import util

DEMO_POEMS = (
    "Am Horizont, wo Lichter blüh'n,\nzeigt die Uhr 17:17, in Abendglüh'n.",
    "Beim Dämmerlicht, so zart und fein, \nschlägt es 17:16, der Tag neigt sich dem Sein.",
    "Die Schatten lang, der Abend naht, \n17:15, in stiller Stadt.",
    "Das Tageslicht schwindet sacht,\n17:14, die Nacht erwacht.",
    "In sanftem Licht, das Abendrot, \nzeigt 17:13, der Tag im Lot.",
    "Der Tag neigt sich, leis und mild,\num 17:12, die Welt verhüllt.",
)
# Generous enough for a local model that has to be loaded first
API_TIMEOUT = 120

_client = None


def _openai():
    # Imported on demand: loading the SDK takes about 15 seconds on a Pi Zero,
    # and most runs show a stored poem without ever calling the API.
    import openai  # pylint: disable=import-outside-toplevel
    return openai


def client():
    """OpenAI compatible client. OPENAI_BASE_URL points it to another server, e.g. Ollama."""
    global _client
    if _client is None:
        if not os.environ.get("OPENAI_API_KEY"):
            sys.exit("[error] Missing openai api key")
        # An empty OPENAI_BASE_URL from .env.dist would otherwise break the SDK default
        base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        _client = _openai().OpenAI(base_url=base_url, timeout=API_TIMEOUT, max_retries=1)
    return _client


def show(clock_time: str, poem: str, stored: bool = False) -> None:
    footer = clock_time if util.env_bool("CLOCKWORK_SHOW_TIME") else False
    display.draw_text(poem, footer, stored)


def current_time_poem(override_time: str | None = None) -> None:
    logging.info("[info] Create current time poem")
    clock_time = override_time or datetime.now().strftime("%H:%M")

    daily = fs.read_daily(clock_time)
    if daily:
        _log("daily", clock_time, daily)
        show(clock_time, daily)
        return

    if util.env_bool("CLOCKWORK_REUSE") and prefer_storage() and show_stored(clock_time):
        return

    poem = generate(clock_time)
    if poem:
        _log("openai", clock_time, poem)
        fs.write(clock_time, poem)
        show(clock_time, poem)
        return

    # API unreachable, fall back to a stored poem for some kind of offline mode
    show_stored(clock_time)


def generate(clock_time: str) -> str | None:
    system = os.environ.get("OPENAI_CLOCKWORK_SYSTEM_PROMPT", "")
    poem = ask_ai(system, clock_time)
    if not poem or not util.env_bool("CLOCKWORK_VALIDATE"):
        return poem

    validation = os.environ.get("OPENAI_CLOCKWORK_VALIDATION_PROMPT", "").replace("<current_time>", clock_time)
    corrected = ask_ai(system, clock_time, poem, validation)
    if not corrected:
        return poem

    logging.info("[openai] %s (correct) //  \"%s\" --> \"%s\"", clock_time, _one_line(poem), _one_line(corrected))
    return corrected


def ask_ai(system: str, user: str, assistant: str | None = None, validation: str | None = None) -> str | None:
    logging.info("[openai] request: %s", user)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if assistant is not None and validation is not None:
        messages += [
            {"role": "assistant", "content": assistant},
            {"role": "user", "content": validation},
        ]

    openai = _openai()
    try:
        completion = client().chat.completions.create(messages=messages, model=os.environ.get("OPENAI_API_MODEL"))
    except openai.APIError as error:
        logging.error("[openai] Request failed: %s", error)
        return None
    return completion.choices[0].message.content


def show_stored(clock_time: str) -> bool:
    poem = fs.read(clock_time)
    if not poem:
        return False

    _log("local", clock_time, poem)
    show(clock_time, poem, stored=True)
    return True


def prefer_storage() -> bool:
    """Decide between API and storage. CLOCKWORK_RANDOM_FACTOR=8 means 1 (api) to 8 (storage)."""
    factor = util.env_int("CLOCKWORK_RANDOM_FACTOR", 1)
    return random.randrange(factor + 1) != 0


def demo() -> None:
    print("[info] Demo")
    for poem in DEMO_POEMS:
        display.draw_text(poem, "Demo")
        time.sleep(4)


def _one_line(text: str) -> str:
    return text.replace("\r", "").replace("\n", "")


def _log(source: str, clock_time: str, poem: str) -> None:
    logging.info("[%s] %s // \"%s\"", source, clock_time, _one_line(poem))
