# exp2012 source-closure builder

This repository turns the supplied Minecraft 1.12 sky, cloud, weather, light, OptiFine, and ShaderMod export into a deterministic, buildable project without rewriting the archived Java source.

## What builds

The project builds a standalone Java 8-compatible builder/inspection JAR that:

- validates both supplied manifests and every recorded SHA-256;
- overlays the 108 host Java files and 30 focused Java files into one assembled source tree, with focused files taking precedence on the 15 exact duplicate paths;
- converts the 26 canonical section-only `.txt` exports into generated Java descriptor classes while keeping the exact text unchanged as classpath resources;
- inventories the remaining host boundary instead of fabricating behavior for absent Minecraft classes;
- runs a deterministic headless Java2D CPU showcase using the supplied vanilla environment textures and the preserved celestial-angle, sunrise/fog, moon-phase, and seeded-star algorithms.

The archived source closure itself is intentionally not claimed as a complete Minecraft client. Its own audit identifies 269 generic host-boundary classes outside the supplied export. The builder compiles and runs independently, while preserving and connecting the supplied material for inspection and later integration with a complete MCP 9.40 workspace.

## Build and run

Windows:

```text
build.cmd
run.cmd
```

Any platform with Python 3 and JDK 11 or newer:

```text
python tools/build.py
java -jar build/exp2012-builder.jar all --archive source-export --output showcase
```

Outputs:

- `build/exp2012-builder.jar`
- `build/assembled-src/` — deduplicated original Java source overlay
- `build/generated-src/` — Java classes generated for section exports
- `build/reports/build-report.json`
- `showcase/*.png` — CPU-rendered validation images

## Source preservation

`source-export.parts/` stores a Base64-chunked slim archive of all supplied Java, GLSL, text, manifests, and environment textures. The five copied LWJGL JAR/DLL binaries are omitted because the headless CPU builder does not load them. The builder also accepts the complete original `source-export.zip` or an extracted `source-export/` directory when present. The verifier checks the supplied hashes before compilation and rendering.

## Complete local archive

The full local package produced in ChatGPT retains the original LWJGL binaries as well. The GitHub checkout intentionally uses the slim chunk archive so all code and source-study material remain present while the build stays small and deterministic.
