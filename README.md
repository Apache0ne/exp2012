# exp2012 source-closure builder

This repository preserves and connects the supplied Minecraft 1.12 sky, cloud, weather, light, OptiFine, and ShaderMod source closure without rewriting the archived Java code.

## Repository state

The repository now contains:

- the builder, verifier, generated-section index, and CPU reference renderer;
- the expanded focused source, section extracts, textures, manifests, and LWJGL files;
- the complete canonical source closure under `source-export.parts/`, including all 108 host files;
- `tools/materialize_source.py`, which restores the exact host tree to `glue/full-files/host/src/minecraft/` and verifies every recorded hash.

The canonical archive is retained so a browser upload, incomplete folder copy, or deleted generated host tree cannot silently remove source. Materialization is deterministic and byte-preserving.

## Build on Windows

```text
build.cmd
```

`build.cmd` performs these steps:

1. materializes the complete export into the checkout;
2. verifies 295 manifest rows and 295 SHA-256 values;
3. confirms the 108-file host tree;
4. overlays 108 host files and 37 focused files, with 15 focused overrides;
5. generates 26 Java descriptor classes for 129 exact source sections;
6. compiles the Java 8-compatible builder JAR;
7. runs the verifier and six headless CPU renders.

## Build on other platforms

```text
python tools/materialize_source.py
python tools/materialize_source.py --check
python tools/build.py
```

The builder requires Python 3 and JDK 11 or newer. Compilation targets Java 8 bytecode with `javac --release 8`.

## Build outputs

- `build/exp2012-builder.jar`
- `build/assembled-src/` — 123 unique package-correct archived Java files
- `build/generated-src/` — generated Java descriptors for the section exports
- `build/reports/build-report.json`
- `showcase/*.png` — six CPU-rendered validation images

## Verified result

The local clean build validates all 295 supplied files and reproduces this JAR hash:

```text
d5a669f06e220601bf15db0de068635f3eaf97018d614d921f4a4cb6660193f5
```

No GitHub Actions, GPU, OpenGL context, Gradle download, Maven download, or network access is used.

## Scope boundary

The supplied closure is not a complete Minecraft client. Its audit identifies 269 external generic Minecraft/Forge host classes. The project does not generate fake stubs or modify archived behavior to hide that boundary. It builds the source assembler, verifier, section registry, and CPU reference runtime while leaving the untouched assembled source ready for a complete MCP 9.40 host workspace.

See `docs/ARCHITECTURE.md`, `docs/LOCAL_BUILD_REPORT.md`, and `docs/HOST_BOUNDARY_REPORT.md` for details.
