from pathlib import Path

from PIL import Image


def test_windows_icon_has_transparent_native_sizes():
    path = Path(__file__).resolve().parents[1] / "web/assets/brand/LohnMail.ico"
    with Image.open(path) as icon:
        assert icon.ico.sizes() == {(n, n) for n in (16, 20, 24, 32, 40, 48, 64, 128, 256)}
        for size in icon.ico.sizes():
            frame = icon.ico.getimage(size).convert("RGBA")
            alpha = frame.getchannel("A")
            assert alpha.getextrema() == (0, 255)
            assert all(frame.getpixel(point)[3] == 0 for point in (
                (0, 0), (size[0]-1, 0), (0, size[1]-1), (size[0]-1, size[1]-1)
            ))
            # Reject a tiny logo floating inside a large transparent canvas.
            left, top, right, bottom = alpha.getbbox()
            assert right - left >= size[0] * 0.75
            assert bottom - top >= size[1] * 0.75
