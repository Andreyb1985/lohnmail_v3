from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_store_pipeline_requires_approved_transparent_artifacts():
    windows = ROOT / 'variants/windows'
    manifest = ET.parse(windows / 'msix/AppxManifest.xml.in')
    ns = {'uap': 'http://schemas.microsoft.com/appx/manifest/uap/windows10'}
    assert manifest.find('.//uap:VisualElements', ns).get('BackgroundColor') == 'transparent'
    assert manifest.find('.//uap:SplashScreen', ns).get('BackgroundColor') == 'transparent'
    build = (windows / 'build-store.ps1').read_text()
    assert '--listing-output $ListingRoot' in build
    assert '--listing-icon $ListingIcon' in build
    assert '--root $ValidationRoot' in build
    standalone = (windows / 'build-standalone.ps1').read_text()
    assert '59e6e29deb593e68c54349e3dccbdb20934ec5b3953c09fe5cd7ae86adf4a640' in standalone
    assert standalone.index('Get-FileHash -LiteralPath $IconPath') < standalone.index('Remove-Item')
    assert '"--icon", $IconPath' in standalone
    workflow = (ROOT.parent / '.github/workflows/build-windows-store.yml').read_text()
    assert 'dist/store/store-listing/*.png' in workflow
