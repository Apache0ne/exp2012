from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "source-export"
ARCHIVE_ZIP = ROOT / "source-export.zip"
ARCHIVE_PARTS = ROOT / "source-export.parts"
BUILD = ROOT / "build"
CLASSES = BUILD / "classes"
GENERATED = BUILD / "generated-src"
ASSEMBLED = BUILD / "assembled-src"
REPORTS = BUILD / "reports"
JAR = BUILD / "exp2012-builder.jar"
SHOWCASE = ROOT / "showcase"


def prepare_archive() -> Path:
    if ARCHIVE.is_dir():
        return ARCHIVE
    archive_zip = ARCHIVE_ZIP
    if not archive_zip.is_file() and ARCHIVE_PARTS.is_dir():
        import base64
        parts = sorted(ARCHIVE_PARTS.glob("part-*.b64"))
        if not parts:
            raise RuntimeError(f"No source archive chunks found in: {ARCHIVE_PARTS}")
        archive_zip = BUILD / "source-export-from-parts.zip"
        encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
        archive_zip.write_bytes(base64.b64decode(encoded, validate=True))
    if not archive_zip.is_file():
        raise RuntimeError(
            f"Missing source archive directory, ZIP, or chunk directory: {ARCHIVE} / {ARCHIVE_ZIP} / {ARCHIVE_PARTS}"
        )
    import zipfile
    extraction = BUILD / "source-export"
    if extraction.exists():
        shutil.rmtree(extraction)
    extraction.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_zip, "r") as archive:
        for info in archive.infolist():
            candidate = (extraction / info.filename).resolve()
            if extraction.resolve() not in candidate.parents and candidate != extraction.resolve():
                raise RuntimeError(f"Unsafe ZIP entry: {info.filename}")
        archive.extractall(extraction)
    children = [path for path in extraction.iterdir() if path.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extraction


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: Path, destination_root: Path) -> tuple[int, int, int]:
    rows = 0
    checked = 0
    skipped_external = 0
    with manifest.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not reader.fieldnames or "destination" not in reader.fieldnames or "sha256" not in reader.fieldnames:
            raise RuntimeError(f"Bad manifest schema: {manifest}")
        for row in reader:
            if not row or not row.get("destination"):
                continue
            rows += 1
            expected = (row.get("sha256") or "").strip()
            if not expected or expected == "-":
                continue
            relative = row["destination"].replace("\\", "/")
            destination = (destination_root / relative).resolve()
            if destination_root.resolve() not in destination.parents and destination != destination_root.resolve():
                raise RuntimeError(f"Unsafe manifest destination: {relative}")
            if not destination.is_file():
                if (row.get("type") or "").strip() == "external-binary":
                    skipped_external += 1
                    continue
                raise RuntimeError(f"Missing manifest destination: {destination}")
            actual = sha256(destination)
            checked += 1
            if actual.lower() != expected.lower():
                raise RuntimeError(
                    f"SHA-256 mismatch: {destination}\nexpected={expected}\nactual={actual}"
                )
    return rows, checked, skipped_external


def copy_tree_overlay(source: Path, destination: Path) -> tuple[int, int]:
    copied = 0
    overwritten = 0
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        if target.exists():
            overwritten += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied, overwritten


def java_identifier(text: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", text)
    value = "_".join(part[:1].upper() + part[1:] for part in parts)
    if not value or value[0].isdigit():
        value = "Section_" + value
    return value


def java_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def canonical_sections() -> list[tuple[str, Path, Path]]:
    sections: list[tuple[str, Path, Path]] = []
    primary = ARCHIVE / "sections"
    host = ARCHIVE / "glue" / "sections" / "host-access"
    for path in sorted(primary.rglob("*.txt")):
        sections.append(("Primary", path.relative_to(primary), path))
    for path in sorted(host.rglob("*.txt")):
        sections.append(("Host", path.relative_to(host), path))
    return sections


def generate_section_classes() -> list[dict[str, object]]:
    package_dir = GENERATED / "dev" / "apacheone" / "exp2012" / "archive"
    package_dir.mkdir(parents=True, exist_ok=True)
    resource_root = CLASSES / "archive-sections"
    records: list[dict[str, object]] = []

    for scope, relative, source in canonical_sections():
        key = f"{scope}/{relative.as_posix()}"
        class_name = "Section_" + java_identifier(key)
        resource_path = f"archive-sections/{key}"
        text = source.read_text(encoding="utf-8-sig")
        section_count = len(re.findall(r"^===== SOURCE LINES ", text, flags=re.MULTILINE))
        if section_count == 0:
            section_count = len(re.findall(r"^===== ", text, flags=re.MULTILINE))
        digest = sha256(source)
        origin_match = re.search(r"(?:Extracted sections from|SOURCE):\s*([^\r\n]+)", text)
        origin = origin_match.group(1).strip() if origin_match else relative.as_posix()

        java_source = f'''package dev.apacheone.exp2012.archive;

/** Generated descriptor. The exact exported text remains unchanged in the matching resource. */
public final class {class_name} {{
    private {class_name}() {{
    }}

    public static SectionDescriptor descriptor() {{
        return new SectionDescriptor(
                "{java_string(resource_path)}",
                "{java_string(origin)}",
                "{digest}",
                {section_count});
    }}
}}
'''
        (package_dir / f"{class_name}.java").write_text(java_source, encoding="utf-8", newline="\n")
        resource_target = resource_root / scope / relative
        resource_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, resource_target)
        records.append(
            {
                "scope": scope,
                "relative": relative.as_posix(),
                "class_name": class_name,
                "resource_path": resource_path,
                "sha256": digest,
                "section_count": section_count,
                "origin": origin,
            }
        )

    registry_lines = [
        "package dev.apacheone.exp2012.archive;",
        "",
        "import java.util.Arrays;",
        "import java.util.Collections;",
        "import java.util.List;",
        "",
        "public final class GeneratedSectionRegistry {",
        "    private GeneratedSectionRegistry() {",
        "    }",
        "",
        "    public static List<SectionDescriptor> all() {",
        "        return Collections.unmodifiableList(Arrays.asList(",
    ]
    for index, record in enumerate(records):
        suffix = "," if index + 1 < len(records) else ""
        registry_lines.append(f"                {record['class_name']}.descriptor(){suffix}")
    registry_lines.extend(["        ));", "    }", "}", ""])
    (package_dir / "GeneratedSectionRegistry.java").write_text("\n".join(registry_lines), encoding="utf-8")
    return records


def copy_runtime_resources() -> None:
    environment = ARCHIVE / "full-files" / "src" / "minecraft" / "assets" / "minecraft" / "textures" / "environment"
    target = CLASSES / "assets" / "minecraft" / "textures" / "environment"
    target.mkdir(parents=True, exist_ok=True)
    for image in sorted(environment.glob("*.png")):
        shutil.copy2(image, target / image.name)


def run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command))
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def locate_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool not found on PATH: {name}")
    return path


def image_probe(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG output: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width < 1 or height < 1 or len(set(data[33:])) < 16:
        raise RuntimeError(f"PNG output appears empty: {path}")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    global ARCHIVE
    parser = argparse.ArgumentParser(description="Build, verify, and run exp2012 locally.")
    parser.add_argument("--clean", action="store_true", help="Delete build products before rebuilding.")
    parser.add_argument("--skip-render", action="store_true", help="Compile and verify without rendering images.")
    args = parser.parse_args()

    started = time.time()
    if args.clean and BUILD.exists():
        shutil.rmtree(BUILD)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    CLASSES.mkdir(parents=True, exist_ok=True)
    GENERATED.mkdir(parents=True, exist_ok=True)
    ASSEMBLED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    SHOWCASE.mkdir(parents=True, exist_ok=True)

    ARCHIVE = prepare_archive()
    print(f"Source archive: {ARCHIVE}")

    main_rows, main_checked, main_skipped = verify_manifest(ARCHIVE / "manifest.tsv", ARCHIVE)
    glue_rows, glue_checked, glue_skipped = verify_manifest(ARCHIVE / "glue" / "manifest.tsv", ARCHIVE / "glue")
    skipped_external = main_skipped + glue_skipped
    print(f"Manifest verification PASS: rows={main_rows + glue_rows}, files={main_checked + glue_checked}, optional-external-skipped={skipped_external}")

    host_root = ARCHIVE / "glue" / "full-files" / "host" / "src" / "minecraft"
    focused_root = ARCHIVE / "full-files" / "src" / "minecraft"
    host_copied, _ = copy_tree_overlay(host_root, ASSEMBLED)
    focused_copied, overwritten = copy_tree_overlay(focused_root, ASSEMBLED)
    assembled_java = len(list(ASSEMBLED.rglob("*.java")))
    print(
        f"Assembled source overlay: host={host_copied}, focused={focused_copied}, "
        f"focused-overrides={overwritten}, unique-java={assembled_java}"
    )

    sections = generate_section_classes()
    copy_runtime_resources()
    print(f"Generated Java descriptors: {len(sections)}")

    java_sources = sorted((ROOT / "src" / "main" / "java").rglob("*.java")) + sorted(GENERATED.rglob("*.java"))
    source_list = BUILD / "sources.list"
    source_list.write_text("\n".join(str(path) for path in java_sources) + "\n", encoding="utf-8")

    javac = locate_tool("javac")
    jar = locate_tool("jar")
    java = locate_tool("java")
    javac_version = run([javac, "-version"]).stdout.strip()
    java_version = run([java, "-version"]).stdout.splitlines()[0]

    run([javac, "--release", "8", "-Xlint:-options", "-encoding", "UTF-8", "-d", str(CLASSES), "@" + str(source_list)])
    run([jar, "--create", "--file", str(JAR), "--main-class", "dev.apacheone.exp2012.Main", "-C", str(CLASSES), "."])
    jar_hash = sha256(JAR)

    verify_run = run([java, "-Djava.awt.headless=true", "-jar", str(JAR), "verify", "--archive", str(ARCHIVE)])
    rendered: list[dict[str, object]] = []
    render_output = ""
    if not args.skip_render:
        render_run = run([java, "-Djava.awt.headless=true", "-jar", str(JAR), "render", "--output", str(SHOWCASE)])
        render_output = render_run.stdout
        for image in sorted(SHOWCASE.glob("*.png")):
            rendered.append(image_probe(image))
        if len(rendered) < 6:
            raise RuntimeError(f"Expected at least 6 rendered PNGs, found {len(rendered)}")

    report = {
        "status": "PASS",
        "duration_seconds": round(time.time() - started, 3),
        "archive": {
            "manifest_rows": main_rows + glue_rows,
            "hash_checked_files": main_checked + glue_checked,
            "optional_external_binaries_skipped": skipped_external,
            "raw_java_files": len(list(ARCHIVE.rglob("*.java"))),
            "raw_text_files": len(list(ARCHIVE.rglob("*.txt"))),
        },
        "assembly": {
            "host_files_copied": host_copied,
            "focused_files_copied": focused_copied,
            "focused_overrides": overwritten,
            "unique_java_files": assembled_java,
        },
        "generated_sections": {
            "classes": len(sections),
            "total_code_sections": sum(int(record["section_count"]) for record in sections),
            "records": sections,
        },
        "compiler": {
            "javac": javac_version,
            "java": java_version,
            "target_release": 8,
            "compiled_sources": len(java_sources),
        },
        "jar": {
            "path": JAR.relative_to(ROOT).as_posix(),
            "bytes": JAR.stat().st_size,
            "sha256": jar_hash,
        },
        "verification_stdout": verify_run.stdout,
        "render_stdout": render_output,
        "images": rendered,
    }
    report_json = REPORTS / "build-report.json"
    report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    markdown = [
        "# Local build report",
        "",
        "**Status: PASS**",
        "",
        f"- Manifest rows validated: {main_rows + glue_rows}",
        f"- Files SHA-256 checked: {main_checked + glue_checked}",
        f"- Optional external LWJGL binaries omitted from slim archive: {skipped_external}",
        f"- Original Java files retained: {len(list(ARCHIVE.rglob('*.java')))}",
        f"- Unique Java files in assembled overlay: {assembled_java}",
        f"- Canonical section `.txt` files converted to Java descriptors: {len(sections)}",
        f"- Builder/generated Java sources compiled: {len(java_sources)}",
        f"- Compiler target: Java 8 (`--release 8`)",
        f"- JAR SHA-256: `{jar_hash}`",
        f"- CPU-rendered PNGs validated: {len(rendered)}",
        "",
        "The archived Minecraft source remains byte-preserved. The runnable JAR is the builder, verifier, section index, and headless CPU reference renderer. The supplied source audit still identifies 269 external host-boundary classes, so this report does not mislabel the partial export as a complete Minecraft client.",
    ]
    (REPORTS / "BUILD_REPORT.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")

    print("=" * 96)
    print("FINAL_STATUS=PASS")
    print(f"JAR={JAR}")
    print(f"JAR_SHA256={jar_hash}")
    print(f"REPORT={report_json}")
    print(f"IMAGES={len(rendered)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FINAL_STATUS=FAIL: {exc}", file=sys.stderr)
        raise
