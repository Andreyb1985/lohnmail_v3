from pathlib import Path
import importlib.util
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_msix_shell_assets_separate_light_plates_from_transparent_taskbar(tmp_path):
    spec = importlib.util.spec_from_file_location('msix_assets', ROOT / 'variants/windows/build-msix-assets.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate(tmp_path)
    with Image.open(ROOT / 'web/assets/brand/lohnmail-app-icon-previous.png') as source:
        artwork = source.convert('RGBA')
    for size in module.TARGET_SIZES:
        expected = artwork.resize((size, size), Image.Resampling.LANCZOS)
        for form in module.FORMS:
            with Image.open(tmp_path / f'Square44x44Logo.targetsize-{size}{form}.png') as im:
                assert im.size == (size, size)
                if form:
                    transparent = Image.new('RGBA', expected.size, (0,0,0,0))
                    transparent.alpha_composite(expected)
                    assert im.tobytes() == transparent.tobytes()
                    assert im.getchannel('A').getextrema() == (0, 255)
                    assert im.getpixel((0, 0))[3] == 0
                    left, top, right, bottom = im.getchannel('A').getbbox()
                    assert right-left >= size*.75 and bottom-top >= size*.75
                else:
                    plated = Image.new('RGBA', expected.size, (245,248,251,255))
                    plated.alpha_composite(expected)
                    assert im.tobytes() == plated.tobytes()
    with Image.open(tmp_path / 'Square44x44Logo.png') as im:
        assert im.getchannel('A').getextrema() == (255,255)
        assert im.getpixel((0,0)) == (245,248,251,255)
    for scale in module.SCALES:
        with Image.open(tmp_path / f'Square44x44Logo.scale-{scale}.png') as im:
            assert im.size == ((44*scale+50)//100,)*2
    files = list(tmp_path.glob('*.png'))
    assert len(files) == 62
    for path in files:
        with Image.open(path) as im:
            if 'altform-' not in path.name:
                assert im.getchannel('A').getextrema() == (255,255), path.name
                assert im.getpixel((0,0)) == (245,248,251,255), path.name
