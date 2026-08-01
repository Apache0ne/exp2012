# exp2012 source-closure builder

This repository turns the supplied Minecraft 1.12 sky, cloud, weather, light, OptiFine, and ShaderMod export into a deterministic local build without rewriting the archived Java source.

## What it does

The builder:

- validates both supplied manifests and their recorded SHA-256 values;
- overlays 108 host files and 37 focused files into one package-correct tree, with the focused copy winning on 15 exact duplicates;
- converts 26 canonical section-only `.txt` exports into generated Java descriptor classes while retaining each exact text file as a classpath resource;
- inventories the unresolved host boundary instead of fabricating behavior for absent Minecraft classes;
- compiles a Java 8-compatible verifier and inspection JAR;
- runs a deterministic headless Java2D CPU showcase using the supplied environment textures and preserved celestial-angle, sunrise/fog, moon-phase, and seeded-star algorithms.

The supplied source closure is not a complete Minecraft client. Its own audit identifies 269 external host-boundary classes. The builder compiles and runs independently, while assembling the untouched source for later placement over a complete MCP 9.40 workspace.

## Source input

Place either of these at the repository root:

- the supplied archive renamed to `source-export.zip`; or
- its extracted contents in `source-export/`.

The builder also accepts an optional Base64-chunked ZIP or TAR.XZ under `source-export.parts/`.

The complete downloadable project produced with this repository includes the original supplied archive. The public GitHub repository contains the builder and integration code rather than duplicating the supplied third-party source bundle and copied LWJGL binaries.

## Build and run

Windows:

```text
build.cmd
```

Any platform with Python 3 and JDK 11 or newer:

```text
python tools/build.py
```

The compiler targets Java 8 bytecode with `javac --release 8`. No GitHub Actions, GPU, OpenGL context, Gradle download, Maven download, or network access is used.

## Outputs

- `build/exp2012-builder.jar`
- `build/assembled-src/` — deduplicated original Java source overlay
- `build/generated-src/` — Java classes generated from canonical `.txt` sections
- `build/reports/build-report.json`
- `showcase/*.png` — CPU-rendered validation images

See `docs/ARCHITECTURE.md` and `docs/LOCAL_BUILD_REPORT.md` for the exact boundary and verified local results.
