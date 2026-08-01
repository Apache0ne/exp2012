# Local build report

**Status: PASS**

- Manifest rows validated: 295
- Files SHA-256 checked: 290
- Optional external LWJGL binaries omitted from slim archive: 5
- Original Java files retained: 138
- Unique Java files in assembled overlay: 123
- Canonical section `.txt` files converted to Java descriptors: 26
- Builder/generated Java sources compiled: 31
- Compiler target: Java 8 (`--release 8`)
- JAR SHA-256: `a041df6a32639ff82e61d9be8ca6db41b88a6c494d0a73e83614843a1ef1efc3`
- CPU-rendered PNGs validated: 6

The archived Minecraft source remains byte-preserved. The runnable JAR is the builder, verifier, section index, and headless CPU reference renderer. The supplied source audit still identifies 269 external host-boundary classes, so this report does not mislabel the partial export as a complete Minecraft client.
