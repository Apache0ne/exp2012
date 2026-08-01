# Architecture

## Canonical and expanded source

`source-export.parts/` is the canonical byte-preserved source closure. It contains the complete supplied export, including the 108 host Java files, 37 focused files, section extracts, textures, manifests, and copied LWJGL binaries.

The repository also carries an expanded study view. `tools/materialize_source.py` reconstructs the canonical archive and copies its exact contents into the normal checkout paths, including:

```text
glue/full-files/host/src/minecraft/
full-files/src/minecraft/
sections/
glue/sections/
```

Materialization verifies the canonical archive before copying and verifies the expanded checkout afterward. It requires exactly 108 files under the host source root and validates all 295 manifest hashes. Existing identical files are not rewritten.

`tools/build.py` prefers a complete expanded checkout. When the host tree is absent, it can still build directly from `source-export.zip`, `source-export/`, or the Base64 chunks in `source-export.parts/`.

## Assembly

The builder creates `build/assembled-src/` in two layers:

1. `glue/full-files/host/src/minecraft`
2. `full-files/src/minecraft`

The focused layer intentionally wins on the 15 duplicate paths. This yields 123 unique archived Java files from the 138 supplied Java files.

## Section conversion

The `.txt` files are exact ranges taken from mixed host classes. Renaming them to `.java` would create invalid compilation units and destroy their source coordinates. The builder instead generates one Java descriptor class per canonical section file. Each descriptor records the original class or path, SHA-256, section count, and classpath resource containing the exact unchanged text.

Canonical inputs are:

- 19 focused and closure section files under `sections/`;
- 7 host-contract files under `glue/sections/host-access/`.

The duplicated copies under `glue/sections/existing/` remain preserved but are not generated twice. The export produces 26 descriptor classes plus one registry, covering 129 extracted source sections.

## Runnable module

The standalone JAR contains:

- archive and expanded-checkout hash verification;
- generated section registry;
- deterministic Java2D CPU renderer;
- supplied environment textures.

It compiles with `javac --release 8` and runs headlessly. No GitHub Actions, GPU, OpenGL context, Gradle or Maven download, or network dependency is used.

## Host boundary

The supplied audit lists 269 external Minecraft, Forge, gameplay, GUI, networking, world-generation, and full-renderer classes. Fabricating empty stubs would make compilation appear successful while disconnecting behavior. The project therefore compiles the builder and reference runtime, retains the archived source unchanged, and leaves the assembled source ready for placement over a complete MCP 9.40 workspace.
