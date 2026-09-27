"""Command line entry point."""

from __future__ import annotations

import argparse
import os
import re
import sys

import display
import fs
import poem
import util

TIME_PATTERN = re.compile(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")


def main() -> None:
    print("### \033[1m\033[4mclockwork\033[0m\033[1m/ai\033[0m ###")
    args = get_arguments()
    util.init()
    util.DRY_RUN = args.dry_run

    if fs.is_locked():
        print("[warning] Display is currently locked, skipping execution")
        return

    fs.lock()
    try:
        run_function(args)
    finally:
        fs.unlock()


def run_function(args: argparse.Namespace) -> None:
    function = args.function
    if function is not None and function not in util.SUPPORTED_FUNCTIONS and not TIME_PATTERN.match(function):
        sys.exit("[error] Not supported function")

    if function == "clear":
        display.clear()
    elif function == "intro":
        display.intro()
    elif function == "demo":
        display.intro()
        poem.demo()
        display.clear()
    elif function == "display":
        print("[info] Custom display")
        display.draw_text(args.additional, "Custom", True)
    elif function == "ask":
        print("[info] Ask")
        answer = poem.ask_ai(os.environ.get("OPENAI_ASK_PROMPT", ""), args.additional)
        if answer:
            display.draw_text(answer, "Answer")
    else:
        poem.current_time_poem(function)


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clockwork/ai",
        description="Generate ai poems by current time for displaying them on a e-ink display.",
    )
    parser.add_argument("function", nargs="?", help="Function to run, or a time like 09:41")
    parser.add_argument("additional", nargs="?", help="Additional argument for the function")
    parser.add_argument("-dr", "--dry-run", action="store_true", help="Save images under var/debug instead of drawing")
    return parser.parse_args()


if __name__ == "__main__":
    main()
