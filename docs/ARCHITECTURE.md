# Architecture

## Immutable input

The supplied export is read from `source-export.zip`, an extracted `source-export/` directory, or optional Base64 chunks under `source-export.parts/`. The complete local package contains the original archive. The public repository does not duplicate the supplied third-party source bundle or copied LWJGL binaries.

Before any assembly or generation, both manifests are read and every available recorded SHA-256 is checked. No archived Java or section text is rewritten.

## Assembly

`tools/build.py` creates `build/assembled-src/` in two layers:

1. `source-export/glue/full-files/host/src/minecraft`
2. `source-export/full-files/src/minecraft`

The focused layer intentionally wins on the 15 duplicate paths. This yields 123 unique archived Java files in one package-correct tree from 138 supplied Java files.

## Section conversion

The `.txt` files are exact ranges taken from mixed host classes. Blindly renaming them to `.java` would create invalid compilation units and destroy their source coordinates. The builder instead generates one Java descriptor class per canonical section file. Each descriptor records the original class/path, SHA-256, section count, and classpath resource containing the exact unchanged text.

Canonical inputs are:

- 19 focused/closure section files under `source-export/sections/`;
- 7 host-contract files under `source-export/glue/sections/host-access/`.

The duplicated copies under `glue/sections/existing/` remain preserved but are not generated twice. The current export produces 26 descriptor classes plus one registry, covering 129 extracted source sections.

## Runnable module

The standalone JAR contains:

- archive hash verification;
- generated section registry;
- deterministic Java2D CPU renderer;
- supplied environment textures.

It compiles with `javac --release 8` and runs headlessly. No GitHub Actions, GPU, OpenGL context, Gradle/Maven download, or network dependency is used.

## Honest host boundary

The supplied audit explicitly lists 269 external Minecraft/Forge/gameplay/rendering classes. Fabricating empty stubs would make compilation appear successful while disconnecting behavior. The project therefore compiles the builder and reference runtime, retains the original source intact, and leaves the assembled source ready to place over a complete MCP 9.40 workspace.
