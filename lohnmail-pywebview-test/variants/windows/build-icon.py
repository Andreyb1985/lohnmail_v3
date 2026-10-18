"""Encode the existing transparent brand artwork as a multi-resolution ICO.

No background is composited and the shared PNG is never modified.
"""
from pathlib import Path
import hashlib
from io import BytesIO

from PIL import Image

SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def build_icon():
    root = Path(__file__).resolve().parents[2]
    brand = root / "web" / "assets" / "brand"
    if hashlib.sha256((brand / "lohnmail-app-icon-previous.png").read_bytes()).hexdigest() != 'c1160ce7e96c704ea8657310834e423dfe31a1211891a16fd5c1e8d641127deb':
        raise ValueError('Unapproved Windows artwork; existing ICO preserved')
    with Image.open(brand / "lohnmail-app-icon-previous.png") as source:
        if source.mode != "RGBA" or source.getchannel("A").getextrema()[0] != 0:
            raise ValueError("The approved source must have a transparent alpha channel")
        encoded = BytesIO()
        source.save(encoded, format="ICO", sizes=[(n, n) for n in SIZES])
        data = encoded.getvalue()
        if hashlib.sha256(data).hexdigest() != '59e6e29deb593e68c54349e3dccbdb20934ec5b3953c09fe5cd7ae86adf4a640':
            raise ValueError('Encoder output differs from approved ICO; existing ICO preserved')
        (brand / "LohnMail.ico").write_bytes(data)


if __name__ == "__main__":
    build_icon()
