"""Driver wrapper for the waveshare 2.13 inch e-paper display (V3)."""

import sys
from pathlib import Path
from types import SimpleNamespace

import util

sys.path.append(str(Path(__file__).resolve().parent / "lib"))


def init():
    if util.DRY_RUN:
        return SimpleNamespace(width=122, height=250)

    from waveshare_epd import epd2in13_V3  # pylint: disable=import-outside-toplevel,import-error
    epd = epd2in13_V3.EPD()
    epd.init()
    return epd
