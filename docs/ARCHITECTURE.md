# Architecture

## Immutable input

`source-export.parts/` contains a Base64-chunked slim ZIP holding every supplied source/text/GLSL/manifest/texture file. The five LWJGL JAR/DLL copies are omitted from the GitHub slim archive because the CPU builder does not load them. A complete `source-export.zip` or extracted `source-export/` directory takes precedence when available. No archived Java or section text is rewritten.

## Assembly

`tools/build.py` creates `build/assembled-src/` in two layers:

1. `source-export/glue/full-files/host/src/minecraft`
2. `source-export/full-files/src/minecraft`

The focused layer intentionally wins for the 15 duplicate paths. This yields 123 unique archived Java files in one package-correct tree.

## Section conversion

The `.txt` files are exact ranges taken from mixed host classes, so blindly renaming them to `.java` would produce invalid classes and destroy their source coordinates. The builder instead generates one Java descriptor class per canonical section file. Each descriptor records the original destination class, SHA-256, section count, and classpath resource containing the exact unchanged text.

Canonical inputs are:

- 19 focused/closure section files under `source-export/sections/`
- 7 host-contract files under `source-export/glue/sections/host-access/`

The duplicated copies under `glue/sections/existing/` remain archived but are not generated twice.

## Runnable module

The standalone JAR contains:

- archive hash verification;
- generated section registry;
- deterministic Java2D CPU renderer;
- supplied environment textures.

It compiles with `javac --release 8` and runs headlessly. No GitHub Actions, GPU, OpenGL context, or network dependency is used.

## Honest host boundary

The supplied audit explicitly lists 269 external Minecraft/Forge/gameplay/rendering classes. Fabricating empty stubs would make compilation appear successful while disconnecting behavior. This project therefore compiles the builder and reference runtime, retains the original source intact, and leaves the assembled source ready to place over a complete MCP 9.40 workspace later.
