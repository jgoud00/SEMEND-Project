"""Prepare a project-local official Windows solver and TI models; no PATH changes."""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOLVER_URL = "https://ngspice.sourceforge.io/eagle-upgrade/ngspice-Fusion360-Update.7z"
MODELS = [
    ("INA826", "https://www.ti.com/lit/zip/sbomc48", "ina826.lib", "INA826-pspice.lib"),
    ("OPA2376", "https://www.ti.com/lit/zip/sbom309", "OPAx376.LIB", "OPA2376.lib"),
]


def download(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        content = response.read(64*1024*1024+1)
    if len(content) > 64*1024*1024:
        raise ValueError("Download unexpectedly exceeds 64 MiB")
    return content


def adapt_model(text, name):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if name == "INA826":
        text = re.sub(r"(?im)(\.model\s+\S+\s+D)\s+\(", r"\1(", text)
        text = re.sub(r"(?im)^(D\S+\s+\S+\s+\S+\s+\S+)\s+\{AREA\}", r"\1 area={AREA}", text)
    return text


def main():
    directory = ROOT / "circuits/models"
    directory.mkdir(parents=True, exist_ok=True)
    sources = []
    if os.name == "nt":
        tools = ROOT / ".tools"
        tools.mkdir(exist_ok=True)
        archive = tools / "ngspice41.7z"
        content = archive.read_bytes() if archive.is_file() else download(SOLVER_URL)
        if not content.startswith(bytes.fromhex("377abcaf271c")):
            raise ValueError("Unexpected solver archive format")
        archive.write_bytes(content)
        members = subprocess.check_output(["tar.exe", "-tf", str(archive)], text=True).splitlines()
        if not members or any(not name.startswith("Fusion360-Update/") or ".." in PurePosixPath(name).parts or PurePosixPath(name).is_absolute() for name in members):
            raise ValueError("Unsafe solver archive member")
        target = tools / "ngspice41"
        target.mkdir(exist_ok=True)
        subprocess.run(["tar.exe", "-xf", str(archive), "-C", str(target)], check=True)
        sources.append({"name": "ngspice-41 official Fusion360 update, portable Windows", "url": SOLVER_URL, "archive_sha256": hashlib.sha256(content).hexdigest(), "reason": "Current stable download link returned HTTP 404 during implementation; official version-41 bundle used instead."})
    for name, url, member, target in MODELS:
        archive = directory / f"{Path(target).stem}-source.zip"
        content = archive.read_bytes() if archive.is_file() else download(url)
        archive.write_bytes(content)
        with zipfile.ZipFile(io.BytesIO(content)) as source:
            raw = source.read(member)
        text = adapt_model(raw.decode("cp1252"), name)
        (directory / target).write_text(text, encoding="utf-8", newline="\n")
        sources.append({"name": name, "url": url, "archive_sha256": hashlib.sha256(content).hexdigest(), "original_model_sha256": hashlib.sha256(raw).hexdigest(), "adapted_model_sha256": hashlib.sha256((directory / target).read_bytes()).hexdigest(), "adaptation": "Line endings/encoding normalized; INA diode AREA made explicit and D model whitespace normalized. Original archive and vendor copyright retained. These syntax edits do not establish simulator compatibility."})
    (directory / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
    print("Prepared local solver and TI models; source hashes in circuits/models/sources.json")


if __name__ == "__main__":
    main()
