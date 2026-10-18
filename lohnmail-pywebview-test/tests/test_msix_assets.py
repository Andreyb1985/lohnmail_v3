from pathlib import Path
import importlib.util
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_generator():
    spec = importlib.util.spec_from_file_location('msix_assets', ROOT / 'variants/windows/build-msix-assets.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_artwork(path, artwork, dimensions):
    width, height = dimensions
    size = min(dimensions)
    expected = Image.new('RGBA', dimensions, (0, 0, 0, 0))
    expected.alpha_composite(artwork.resize((size, size), Image.Resampling.LANCZOS),
                             ((width-size)//2, (height-size)//2))
    with Image.open(path) as actual:
        assert actual.size == dimensions
        assert actual.convert('RGBA').tobytes() == expected.tobytes(), path.name
        assert actual.getchannel('A').getextrema() == (0, 255)


def test_every_msix_resource_uses_original_transparent_pixels(tmp_path):
    module = load_generator()
    module.generate(tmp_path)
    with Image.open(ROOT / 'web/assets/brand/lohnmail-app-icon-previous.png') as source:
        artwork = source.convert('RGBA')
    expected = {}
    for name, size in (('Square44x44Logo', 44), ('Square150x150Logo', 150), ('StoreLogo', 50)):
        expected[name + '.png'] = (size, size)
        for scale in (100, 125, 150, 200, 400):
            expected[f'{name}.scale-{scale}.png'] = ((size*scale+50)//100,)*2
    for size in (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256):
        for form in ('', '_altform-unplated', '_altform-lightunplated'):
            expected[f'Square44x44Logo.targetsize-{size}{form}.png'] = (size, size)
    expected.update({'Wide310x150Logo.png': (310, 150), 'SplashScreen.png': (620, 300)})
    assert len(expected) == 62
    assert {path.name for path in tmp_path.glob('*.png')} == set(expected)
    for name, dimensions in expected.items():
        assert_artwork(tmp_path / name, artwork, dimensions)


def test_store_listing_is_separate_and_transparent(tmp_path):
    module = load_generator()
    module.generate(tmp_path / 'Assets')
    path = module.generate_listing(tmp_path / 'listing')
    assert path.name == 'Lohn-mail-Store-300x300.png'
    assert not (tmp_path / 'Assets' / path.name).exists()
    assert_artwork(path, module.load_artwork(), (300, 300))


def test_unapproved_artwork_rejected_before_output(tmp_path, monkeypatch):
    module = load_generator()
    source = tmp_path / 'wrong.png'
    image = Image.new('RGBA', (1024, 1024), 'white')
    image.putpixel((0, 0), (0, 0, 0, 0))
    image.save(source)
    monkeypatch.setattr(module, 'ARTWORK_PATH', source)
    with pytest.raises(ValueError, match='user-approved'):
        module.generate(tmp_path / 'Assets')
    assert not (tmp_path / 'Assets').exists()
