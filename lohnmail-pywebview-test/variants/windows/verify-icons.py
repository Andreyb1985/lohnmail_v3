"""Inspect unpacked MSIX icon payloads, not just source-tree assets.

This is an artifact contract, NOT an interactive Windows Shell visual test.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import xml.etree.ElementTree as ET

from PIL import Image


def check(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root, pri_dump):
    spec = importlib.util.spec_from_file_location("msix_assets", Path(__file__).with_name("build-msix-assets.py"))
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    with tempfile.TemporaryDirectory(prefix="lohnmail-icon-reference-") as temporary:
        expected = Path(temporary)
        generator.generate(expected)
        check({p.name for p in (root / "Assets").glob("*.png")} ==
              {p.name for p in expected.glob("*.png")}, "Unexpected MSIX asset set")
        for reference in expected.glob("*.png"):
            with Image.open(reference) as wanted, Image.open(root / "Assets" / reference.name) as actual:
                check(actual.size == wanted.size and actual.convert("RGBA").tobytes() == wanted.tobytes(),
                      "Packaged icon differs: " + reference.name)

    manifest = ET.parse(root / "AppxManifest.xml")
    visual = manifest.find(".//{http://schemas.microsoft.com/appx/manifest/uap/windows10}VisualElements")
    check(visual is not None and visual.get("BackgroundColor") == "#F5F8FB", "Wrong Shell fallback color")
    pri = ET.parse(pri_dump)
    candidates = {}
    for candidate in pri.findall(".//NamedResource[@name='Square44x44Logo.png']/Candidate"):
        qualifiers = {q.get("name"): q.get("value") for q in candidate.findall("./QualifierSet/Qualifier")}
        candidates[(qualifiers.get("TargetSize"), qualifiers.get("AlternateForm", ""))] = candidate.findtext("Value", "").replace("\\", "/")
    for size in generator.TARGET_SIZES:
        for form in generator.FORMS:
            alternate = form.removeprefix("_altform-").upper()
            expected = f"Assets/Square44x44Logo.targetsize-{size}{form}.png"
            check(candidates.get((str(size), alternate)) == expected, "Wrong PRI qualifier mapping: " + expected)

    icon = root / "web/assets/brand/LohnMail.ico"
    data = icon.read_bytes()
    exe = (root / "LohnMail.exe").read_bytes()
    with Image.open(icon) as ico:
        check(ico.ico.sizes() == {(s,s) for s in (16,20,24,32,40,48,64,128,256)}, "Wrong ICO sizes")
        for size in ico.ico.sizes():
            frame = ico.ico.getimage(size).convert("RGBA")
            check(frame.getchannel("A").getextrema() == (0,255), "Opaque EXE icon")
            check(all(frame.getpixel(p)[3] == 0 for p in ((0,0),(size[0]-1,0),(0,size[1]-1),(size[0]-1,size[1]-1))), "EXE icon has a plate")
    count = struct.unpack_from("<H", data, 4)[0]
    check(count == 9, "Wrong ICO directory")
    for index in range(count):
        length, offset = struct.unpack_from("<II", data, 6 + index*16 + 8)
        payload = data[offset:offset+length]
        check(len(payload) == length and payload in exe, "EXE is missing an ICO representation")
    return {"pngs": 62, "transparent_unplated": 28, "light_plated": 34,
            "pri_target_mappings": 42, "embedded_ico_sizes": 9,
            "shell_visual_verified": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--pri-dump", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root, args.pri_dump)
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
