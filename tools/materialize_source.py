from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS_DIR = ROOT / "source-export.parts"
SOURCE_ZIP = ROOT / "source-export.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_target(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    resolved_root = root.resolve()
    if target != resolved_root and resolved_root not in target.parents:
        raise RuntimeError(f"Unsafe archive path: {name}")
    return target


def decode_archive() -> bytes:
    if SOURCE_ZIP.is_file():
        return SOURCE_ZIP.read_bytes()

    parts = sorted(PARTS_DIR.glob("part-*.b64"))
    if not parts:
        raise RuntimeError(
            "Missing source-export.zip and source-export.parts/part-*.b64. "
            "The canonical source archive is required to materialize the checkout."
        )
    encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
    return base64.b64decode(encoded, validate=True)


def extract_archive(payload: bytes, destination: Path) -> Path:
    if payload.startswith(b"PK\x03\x04"):
        archive_path = destination / "source-export.zip"
        archive_path.write_bytes(payload)
        extraction = destination / "extracted"
        extraction.mkdir()
        with zipfile.ZipFile(archive_path, "r") as archive:
            for item in archive.infolist():
                safe_target(extraction, item.filename)
            archive.extractall(extraction)
    elif payload.startswith(b"\xfd7zXZ\x00"):
        archive_path = destination / "source-export.tar.xz"
        archive_path.write_bytes(payload)
        extraction = destination / "extracted"
        extraction.mkdir()
        with tarfile.open(archive_path, "r:xz") as archive:
            for item in archive.getmembers():
                safe_target(extraction, item.name)
            archive.extractall(extraction)
    else:
        raise RuntimeError("Unsupported source archive payload")

    children = [path for path in extraction.iterdir() if path.name != "__MACOSX"]
    return children[0] if len(children) == 1 and children[0].is_dir() else extraction


def verify_manifest(manifest: Path, base: Path) -> tuple[int, int]:
    rows = checked = 0
    with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or not {"destination", "sha256"}.issubset(reader.fieldnames):
            raise RuntimeError(f"Invalid manifest schema: {manifest}")
        for row in reader:
            destination_text = (row.get("destination") or "").strip()
            if not destination_text:
                continue
            rows += 1
            destination = safe_target(base, destination_text.replace("\\", "/"))
            if not destination.is_file():
                raise RuntimeError(f"Missing manifest destination: {destination}")
            expected = (row.get("sha256") or "").strip()
            if expected and expected != "-":
                actual = sha256(destination)
                if actual.lower() != expected.lower():
                    raise RuntimeError(
                        f"SHA-256 mismatch: {destination}\nexpected={expected}\nactual={actual}"
                    )
                checked += 1
    return rows, checked


def verify_export(export_root: Path) -> tuple[int, int]:
    main_rows, main_checked = verify_manifest(export_root / "manifest.tsv", export_root)
    glue_rows, glue_checked = verify_manifest(
        export_root / "glue" / "manifest.tsv", export_root / "glue"
    )
    return main_rows + glue_rows, main_checked + glue_checked


def copy_exact(source: Path, destination: Path) -> int:
    copied = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != path.read_bytes():
            shutil.copy2(path, target)
            copied += 1
    return copied


def host_file_count(root: Path) -> int:
    host = root / "glue" / "full-files" / "host" / "src" / "minecraft"
    return sum(1 for path in host.rglob("*") if path.is_file()) if host.is_dir() else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the exact source export into a normal repository checkout."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the expanded checkout only; do not copy from the canonical archive.",
    )
    args = parser.parse_args()

    if args.check:
        rows, checked = verify_export(ROOT)
        host_files = host_file_count(ROOT)
        if host_files != 108:
            raise RuntimeError(f"Expected 108 expanded host files, found {host_files}")
        print(
            f"Expanded checkout verification PASS: rows={rows}, "
            f"hashes={checked}, host-files={host_files}"
        )
        return 0

    with tempfile.TemporaryDirectory(prefix="exp2012-materialize-") as temp_text:
        canonical = extract_archive(decode_archive(), Path(temp_text))
        source_rows, source_checked = verify_export(canonical)

        copied = 0
        for relative in (
            Path("manifest.tsv"),
            Path("CLOSURE_ADDITIONS.txt"),
            Path("CLOSURE_AUDIT_AFTER_ADDITIONS.txt"),
            Path("README.txt"),
        ):
            source = canonical / relative
            if source.is_file():
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.is_file() or target.read_bytes() != source.read_bytes():
                    shutil.copy2(source, target)
                    copied += 1

        copied += copy_exact(canonical / "full-files", ROOT / "full-files")
        copied += copy_exact(canonical / "sections", ROOT / "sections")
        copied += copy_exact(canonical / "glue", ROOT / "glue")

    rows, checked = verify_export(ROOT)
    host_files = host_file_count(ROOT)
    if host_files != 108:
        raise RuntimeError(f"Expected 108 expanded host files, found {host_files}")
    if (rows, checked) != (source_rows, source_checked):
        raise RuntimeError("Canonical and expanded verification counts differ")

    print(
        "Source materialization PASS: "
        f"copied={copied}, rows={rows}, hashes={checked}, host-files={host_files}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
