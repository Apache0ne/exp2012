from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
CLASSES = BUILD / "classes"
GENERATED = BUILD / "generated-src"
ASSEMBLED = BUILD / "assembled-src"
REPORTS = BUILD / "reports"
JAR = BUILD / "exp2012-builder.jar"
SHOWCASE = ROOT / "showcase"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_target(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    root = root.resolve()
    if target != root and root not in target.parents:
        raise RuntimeError(f"Unsafe archive path: {name}")
    return target


def prepare_archive() -> Path:
    extracted = ROOT / "source-export"
    if extracted.is_dir():
        return extracted

    archive = ROOT / "source-export.zip"
    if not archive.is_file():
        parts = sorted((ROOT / "source-export.parts").glob("part-*.b64"))
        if not parts:
            raise RuntimeError("Provide source-export/, source-export.zip, or source-export.parts/")
        payload = base64.b64decode("".join(p.read_text("ascii").strip() for p in parts), validate=True)
        if payload.startswith(b"PK\x03\x04"):
            archive = BUILD / "source-export-from-parts.zip"
        elif payload.startswith(b"\xfd7zXZ\x00"):
            archive = BUILD / "source-export-from-parts.tar.xz"
        else:
            raise RuntimeError("Unsupported chunk payload")
        archive.write_bytes(payload)

    destination = BUILD / "source-export"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    if archive.suffix.lower() == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                safe_target(destination, item.filename)
            bundle.extractall(destination)
    else:
        with tarfile.open(archive, "r:xz") as bundle:
            for item in bundle.getmembers():
                safe_target(destination, item.name)
            bundle.extractall(destination)

    children = [p for p in destination.iterdir() if p.name != "__MACOSX"]
    return children[0] if len(children) == 1 and children[0].is_dir() else destination


def verify_manifest(manifest: Path, destination_root: Path) -> tuple[int, int, int]:
    rows = checked = skipped = 0
    with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or not {"destination", "sha256"}.issubset(reader.fieldnames):
            raise RuntimeError(f"Invalid manifest: {manifest}")
        for row in reader:
            if not row.get("destination"):
                continue
            rows += 1
            expected = (row.get("sha256") or "").strip()
            if not expected or expected == "-":
                continue
            target = safe_target(destination_root, row["destination"].replace("\\", "/"))
            if not target.is_file():
                if (row.get("type") or "").strip() == "external-binary":
                    skipped += 1
                    continue
                raise RuntimeError(f"Missing manifest destination: {target}")
            actual = sha256(target)
            checked += 1
            if actual.lower() != expected.lower():
                raise RuntimeError(f"SHA-256 mismatch: {target}\nexpected={expected}\nactual={actual}")
    return rows, checked, skipped


def overlay(source: Path, destination: Path) -> tuple[int, int]:
    copied = overwritten = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        target = destination / path.relative_to(source)
        overwritten += int(target.exists())
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied, overwritten


def identifier(text: str) -> str:
    value = "_".join(part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", text))
    return value if value and not value[0].isdigit() else "Section_" + value


def quoted(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def generate_sections(archive: Path) -> list[dict[str, object]]:
    package = GENERATED / "dev/apacheone/exp2012/archive"
    resources = CLASSES / "archive-sections"
    package.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    roots = [("Primary", archive / "sections"), ("Host", archive / "glue/sections/host-access")]
    for scope, root in roots:
        for source in sorted(root.rglob("*.txt")):
            relative = source.relative_to(root)
            key = f"{scope}/{relative.as_posix()}"
            class_name = "Section_" + identifier(key)
            text = source.read_text(encoding="utf-8-sig")
            section_count = len(re.findall(r"^===== SOURCE LINES ", text, re.MULTILINE))
            if not section_count:
                section_count = len(re.findall(r"^===== ", text, re.MULTILINE))
            match = re.search(r"(?:Extracted sections from|SOURCE):\s*([^\r\n]+)", text)
            origin = match.group(1).strip() if match else relative.as_posix()
            digest = sha256(source)
            resource = f"archive-sections/{key}"
            java = f'''package dev.apacheone.exp2012.archive;

/** Generated descriptor; exact exported text is stored in its classpath resource. */
public final class {class_name} {{
    private {class_name}() {{}}
    public static SectionDescriptor descriptor() {{
        return new SectionDescriptor("{quoted(resource)}", "{quoted(origin)}", "{digest}", {section_count});
    }}
}}
'''
            (package / f"{class_name}.java").write_text(java, encoding="utf-8")
            target = resources / scope / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            records.append({"class_name": class_name, "origin": origin, "resource": resource,
                            "sha256": digest, "sections": section_count})

    calls = ",\n".join(f"                {r['class_name']}.descriptor()" for r in records)
    registry = f'''package dev.apacheone.exp2012.archive;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class GeneratedSectionRegistry {{
    private GeneratedSectionRegistry() {{}}
    public static List<SectionDescriptor> all() {{
        return Collections.unmodifiableList(Arrays.asList(
{calls}
        ));
    }}
}}
'''
    (package / "GeneratedSectionRegistry.java").write_text(registry, encoding="utf-8")
    return records


def build_jar() -> None:
    manifest = b"Manifest-Version: 1.0\r\nMain-Class: dev.apacheone.exp2012.Main\r\n\r\n"
    with zipfile.ZipFile(JAR, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        entries = [("META-INF/MANIFEST.MF", manifest)]
        entries.extend((path.relative_to(CLASSES).as_posix(), path.read_bytes())
                       for path in sorted(CLASSES.rglob("*")) if path.is_file())
        for name, data in entries:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)


def command(args: list[str]) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(args))
    result = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}")
    return result


def tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Required tool not found: {name}")
    return found


def png_info(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG: {path}")
    return {"path": path.relative_to(ROOT).as_posix(), "width": int.from_bytes(data[16:20], "big"),
            "height": int.from_bytes(data[20:24], "big"), "bytes": len(data), "sha256": sha256(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, verify, and run exp2012 locally")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    started = time.time()
    if BUILD.exists():
        shutil.rmtree(BUILD)
    for directory in (CLASSES, GENERATED, ASSEMBLED, REPORTS, SHOWCASE):
        directory.mkdir(parents=True, exist_ok=True)

    archive = prepare_archive()
    print(f"Source archive: {archive}")
    a = verify_manifest(archive / "manifest.tsv", archive)
    b = verify_manifest(archive / "glue/manifest.tsv", archive / "glue")
    rows, checked, skipped = (a[0] + b[0], a[1] + b[1], a[2] + b[2])
    print(f"Manifest verification PASS: rows={rows}, files={checked}, optional-external-skipped={skipped}")

    host, _ = overlay(archive / "glue/full-files/host/src/minecraft", ASSEMBLED)
    focused, overwritten = overlay(archive / "full-files/src/minecraft", ASSEMBLED)
    unique_java = len(list(ASSEMBLED.rglob("*.java")))
    records = generate_sections(archive)
    print(f"Assembled source: host={host}, focused={focused}, overrides={overwritten}, unique-java={unique_java}")
    print(f"Generated Java descriptors: {len(records)}")

    textures = archive / "full-files/src/minecraft/assets/minecraft/textures/environment"
    texture_target = CLASSES / "assets/minecraft/textures/environment"
    texture_target.mkdir(parents=True)
    for image in textures.glob("*.png"):
        shutil.copy2(image, texture_target / image.name)

    sources = sorted((ROOT / "src/main/java").rglob("*.java")) + sorted(GENERATED.rglob("*.java"))
    source_list = BUILD / "sources.list"
    source_list.write_text("\n".join(str(p) for p in sources) + "\n", encoding="utf-8")
    javac, java = tool("javac"), tool("java")
    javac_version = command([javac, "-version"]).stdout.strip()
    java_version = command([java, "-version"]).stdout.splitlines()[0]
    command([javac, "--release", "8", "-Xlint:-options", "-encoding", "UTF-8", "-d", str(CLASSES), "@" + str(source_list)])
    build_jar()
    print(f"Built reproducible JAR: {JAR}")
    verify = command([java, "-Djava.awt.headless=true", "-jar", str(JAR), "verify", "--archive", str(archive)])

    images: list[dict[str, object]] = []
    render_output = ""
    if not args.skip_render:
        rendered = command([java, "-Djava.awt.headless=true", "-jar", str(JAR), "render", "--output", str(SHOWCASE)])
        render_output = rendered.stdout
        images = [png_info(path) for path in sorted(SHOWCASE.glob("*.png"))]
        if len(images) < 6:
            raise RuntimeError(f"Expected 6 PNG outputs, found {len(images)}")

    report = {
        "status": "PASS", "duration_seconds": round(time.time() - started, 3),
        "archive": {"manifest_rows": rows, "hash_checked_files": checked,
                    "optional_external_binaries_skipped": skipped,
                    "raw_java_files": len(list(archive.rglob("*.java"))),
                    "raw_text_files": len(list(archive.rglob("*.txt")))},
        "assembly": {"host_files": host, "focused_files": focused, "focused_overrides": overwritten,
                     "unique_java_files": unique_java},
        "generated_sections": {"classes": len(records), "code_sections": sum(int(r["sections"]) for r in records)},
        "compiler": {"javac": javac_version, "java": java_version, "target_release": 8,
                     "compiled_sources": len(sources)},
        "jar": {"path": JAR.relative_to(ROOT).as_posix(), "bytes": JAR.stat().st_size, "sha256": sha256(JAR)},
        "verification_stdout": verify.stdout, "render_stdout": render_output, "images": images,
    }
    (REPORTS / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("=" * 96)
    print("FINAL_STATUS=PASS")
    print(f"JAR={JAR}")
    print(f"JAR_SHA256={report['jar']['sha256']}")
    print(f"REPORT={REPORTS / 'build-report.json'}")
    print(f"IMAGES={len(images)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"FINAL_STATUS=FAIL: {error}", file=sys.stderr)
        raise
