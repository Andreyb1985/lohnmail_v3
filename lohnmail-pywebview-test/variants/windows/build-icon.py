"""Encode the existing transparent brand artwork as a multi-resolution ICO.

No background is composited and the shared PNG is never modified.
"""
from pathlib import Path

from PIL import Image

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def build_icon():
    root = Path(__file__).resolve().parents[2]
    brand = root / "web" / "assets" / "brand"
    with Image.open(brand / "lohnmail-app-icon-previous.png") as source:
        if source.mode != "RGBA" or source.getchannel("A").getextrema()[0] != 0:
            raise ValueError("The approved source must have a transparent alpha channel")
        source.save(brand / "LohnMail.ico", format="ICO", sizes=[(n, n) for n in SIZES])


if __name__ == "__main__":
    build_icon()
