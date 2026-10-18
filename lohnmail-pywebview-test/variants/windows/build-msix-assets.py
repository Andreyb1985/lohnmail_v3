"""Compile MSIX shell assets from the approved transparent Windows artwork.

Generated assets belong to staging, never modify macOS or in-app branding.
All theme/target-size choices must be indexed by MakePRI before MakeAppx.
Every resource uses the user-approved artwork on a transparent canvas. Never
paint a fallback plate into icons; Windows Shell rendering is tested separately.
"""
from pathlib import Path
import argparse
import hashlib
from PIL import Image

TARGET_SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)
SCALES = (100, 125, 150, 200, 400)
FORMS = ("", "_altform-unplated", "_altform-lightunplated")
ARTWORK_PATH = Path(__file__).resolve().parents[2] / 'web/assets/brand/lohnmail-app-icon-previous.png'
APPROVED_ARTWORK_SHA256 = 'c1160ce7e96c704ea8657310834e423dfe31a1211891a16fd5c1e8d641127deb'
APPROVED_ICO_SHA256 = '59e6e29deb593e68c54349e3dccbdb20934ec5b3953c09fe5cd7ae86adf4a640'
LISTING_ICON_NAME = 'Lohn-mail-Store-300x300.png'


def load_artwork():
    if hashlib.sha256(ARTWORK_PATH.read_bytes()).hexdigest() != APPROVED_ARTWORK_SHA256:
        raise ValueError('Windows artwork differs from the user-approved transparent source')
    with Image.open(ARTWORK_PATH) as image:
        artwork = image.convert('RGBA')
    if artwork.getchannel('A').getextrema() != (0, 255):
        raise ValueError('Transparent source artwork required')
    return artwork


def render(artwork, width, height=None):
    height = height or width
    size = min(width, height)
    logo = artwork.resize((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    canvas.alpha_composite(logo, ((width-size)//2, (height-size)//2))
    return canvas


def generate_listing(output: Path):
    """Partner Center listing artwork is separate from MSIX's StoreLogo."""
    artwork = load_artwork()
    output.mkdir(parents=True, exist_ok=True)
    path = output / LISTING_ICON_NAME
    render(artwork, 300).save(path)
    return path


def generate(output: Path):
    artwork = load_artwork()
    output.mkdir(parents=True, exist_ok=True)

    def save(name, width, height=None):
        render(artwork, width, height).save(output / name)

    for base, size in (('Square44x44Logo', 44), ('Square150x150Logo', 150), ('StoreLogo', 50)):
        save(base + '.png', size)
        for scale in SCALES:
            save(f'{base}.scale-{scale}.png', (size*scale+50)//100)
    for size in TARGET_SIZES:
        for form in FORMS:
            save(f'Square44x44Logo.targetsize-{size}{form}.png', size)
    save('Wide310x150Logo.png', 310, 150)
    save('SplashScreen.png', 620, 300)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--listing-output', type=Path)
    args = parser.parse_args()
    if args.listing_output and args.output.resolve() == args.listing_output.resolve():
        parser.error('Listing output must be separate from MSIX Assets')
    generate(args.output)
    if args.listing_output:
        generate_listing(args.listing_output)
