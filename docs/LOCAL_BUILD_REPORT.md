# Local build report

**Status: PASS**

The verification used the complete supplied archive on the ChatGPT CPU runtime. GitHub Actions were not used.

## Complete build

- Manifest rows validated: 295
- Files SHA-256 checked: 295
- Missing manifest files: 0
- Original Java files retained: 138
- Original text files retained: 51
- Host files overlaid: 108
- Focused files overlaid: 37
- Focused-path overrides: 15
- Unique Java files in assembled overlay: 123
- Canonical section `.txt` files converted to Java descriptors: 26
- Extracted source sections indexed: 129
- Builder/generated Java sources compiled: 31
- Compiler: OpenJDK `javac 21.0.10`
- Compiler target: Java 8 (`--release 8`)
- Reproducible builder JAR bytes: 169,758
- Reproducible builder JAR SHA-256: `d5a669f06e220601bf15db0de068635f3eaf97018d614d921f4a4cb6660193f5`
- Consecutive clean-build JAR hashes matched: PASS
- CPU-rendered PNGs validated: 6
- Final compiler result: PASS
- Final archive verification: PASS
- Final CPU render: PASS

## Main-branch repair test

The expanded host tree was deliberately removed from a clean local copy to reproduce the incomplete browser upload. The new `tools/materialize_source.py` workflow then:

- reconstructed the canonical archive;
- restored exactly 108 files under `glue/full-files/host/src/minecraft/`;
- validated 295 manifest rows and 295 SHA-256 values after copying;
- passed `python tools/materialize_source.py --check`;
- completed the compiler, verifier, and six CPU renders;
- reproduced the same JAR SHA-256: `d5a669f06e220601bf15db0de068635f3eaf97018d614d921f4a4cb6660193f5`.

The archived Minecraft, OptiFine, and ShaderMod source remains byte-preserved. The runnable JAR is the builder, verifier, generated-section index, and headless CPU reference renderer. The supplied source audit still identifies 269 external host-boundary classes, so this report does not mislabel the partial export as a complete Minecraft client.
