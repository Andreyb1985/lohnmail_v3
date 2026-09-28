from pathlib import Path
import importlib.util
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def test_msix_shell_assets_have_all_sizes_themes_and_no_white_plate(tmp_path):
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
                assert im.getchannel('A').tobytes() == expected.getchannel('A').tobytes()
                assert im.getchannel('A').getextrema() == (0, 255)
                assert im.getpixel((0, 0))[3] == 0
                left, top, right, bottom = im.getchannel('A').getbbox()
                assert right-left >= size*.75 and bottom-top >= size*.75
    with Image.open(tmp_path / 'Square44x44Logo.png') as im:
        assert im.getchannel('A').tobytes() == artwork.resize((44,44), Image.Resampling.LANCZOS).getchannel('A').tobytes()
    for scale in module.SCALES:
        with Image.open(tmp_path / f'Square44x44Logo.scale-{scale}.png') as im:
            assert im.size == ((44*scale+50)//100,)*2
