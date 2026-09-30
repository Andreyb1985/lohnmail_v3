"""Compile MSIX shell assets from the approved transparent Windows artwork.

Generated assets belong to staging, never modify macOS or in-app branding.
All theme/target-size choices must be indexed by MakePRI before MakeAppx.
Unplated variants remain transparent; legacy plated surfaces get an explicit
light canvas so transparent pixels cannot reveal the Windows accent plate.
"""
from pathlib import Path
import argparse
from PIL import Image

TARGET_SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)
SCALES = (100, 125, 150, 200, 400)
FORMS = ("", "_altform-unplated", "_altform-lightunplated")
PLATE_COLOR = (245, 248, 251, 255)  # #F5F8FB, matching the native caption/UI


def generate(output: Path):
    source = Path(__file__).resolve().parents[2] / 'web/assets/brand/lohnmail-app-icon-previous.png'
    with Image.open(source) as image:
        artwork = image.convert('RGBA')
    if artwork.getchannel('A').getextrema() != (0, 255):
        raise ValueError('Transparent source artwork required')
    output.mkdir(parents=True, exist_ok=True)

    def save(name, width, height=None, *, unplated=False):
        height = height or width
        size = min(width, height)
        logo = artwork.resize((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0) if unplated else PLATE_COLOR)
        canvas.alpha_composite(logo, ((width-size)//2, (height-size)//2))
        canvas.save(output / name)

    for base, size in (('Square44x44Logo', 44), ('Square150x150Logo', 150), ('StoreLogo', 50)):
        save(base + '.png', size)
        for scale in SCALES:
            save(f'{base}.scale-{scale}.png', (size*scale+50)//100)
    for size in TARGET_SIZES:
        for form in FORMS:
            save(f'Square44x44Logo.targetsize-{size}{form}.png', size, unplated=bool(form))
    save('Wide310x150Logo.png', 310, 150)
    save('SplashScreen.png', 620, 300)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    generate(parser.parse_args().output)
