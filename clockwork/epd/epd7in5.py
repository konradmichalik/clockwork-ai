"""Driver wrapper for the waveshare 7.5 inch e-paper display (V2)."""

import sys
from pathlib import Path
from types import SimpleNamespace

import util

sys.path.append(str(Path(__file__).resolve().parent / "lib"))


def init():
    if util.DRY_RUN:
        return SimpleNamespace(width=800, height=480)

    from waveshare_epd import epd7in5_V2  # pylint: disable=import-outside-toplevel,import-error
    epd = epd7in5_V2.EPD()
    epd.init()
    return epd
