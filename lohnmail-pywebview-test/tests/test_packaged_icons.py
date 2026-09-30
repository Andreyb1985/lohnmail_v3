import importlib.util
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "variants/windows" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("corruption", [None, "image", "mapping", "manifest", "exe"])
def test_packaged_icon_validator_rejects_corruption(tmp_path, corruption):
    load("build-msix-assets").generate(tmp_path / "Assets")
    icon = tmp_path / "web/assets/brand/LohnMail.ico"
    icon.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "web/assets/brand/LohnMail.ico", icon)
    # Synthetic bytes test payload matching; the real CI gate reads PyInstaller's EXE.
    (tmp_path / "LohnMail.exe").write_bytes(b"SYNTHETIC" + icon.read_bytes())
    (tmp_path / "AppxManifest.xml").write_text(
        '<Package xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10">'
        '<uap:VisualElements BackgroundColor="#F5F8FB"/></Package>', encoding="utf-8")
    pri = ET.Element("PriInfo")
    resource = ET.SubElement(pri, "NamedResource", name="Square44x44Logo.png")
    for path in (tmp_path / "Assets").glob("*targetsize-*.png"):
        suffix = path.stem.split("targetsize-")[1]
        size, _, form = suffix.partition("_altform-")
        candidate = ET.SubElement(resource, "Candidate", type="Path")
        qualifiers = ET.SubElement(candidate, "QualifierSet")
        ET.SubElement(qualifiers, "Qualifier", name="TargetSize", value=size)
        if form:
            ET.SubElement(qualifiers, "Qualifier", name="AlternateForm", value=form.upper())
        ET.SubElement(candidate, "Value").text = "Assets/" + path.name
    if corruption == "image":
        Image.new("RGBA", (16,16), "blue").save(tmp_path / "Assets/Square44x44Logo.targetsize-16.png")
    elif corruption == "mapping":
        resource.find("./Candidate/Value").text = "Assets/wrong.png"
    elif corruption == "manifest":
        (tmp_path / "AppxManifest.xml").write_text("<Package/>", encoding="utf-8")
    elif corruption == "exe":
        (tmp_path / "LohnMail.exe").write_bytes(b"NO ICON")
    dump = tmp_path / "resources.pri.xml"
    ET.ElementTree(pri).write(dump)
    verifier = load("verify-icons")
    if corruption:
        with pytest.raises(ValueError):
            verifier.verify(tmp_path, dump)
    else:
        result = verifier.verify(tmp_path, dump)
        assert result["pri_target_mappings"] == 42
        assert result["embedded_ico_sizes"] == 9
        assert not result["shell_visual_verified"]
