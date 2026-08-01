# Local build report

**Status: PASS**

The final verification used the complete supplied archive on the ChatGPT CPU runtime. GitHub Actions were not used.

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
- Builder JAR bytes: 177,058
- Builder JAR SHA-256: `91ea4e3cee542010b6e3b905b1e6476d626d3d6970b6b8bc56eb3c0e36380b8f`
- CPU-rendered PNGs validated: 6
- Final compiler result: PASS
- Final archive verification: PASS
- Final CPU render: PASS

The archived Minecraft/OptiFine/ShaderMod source remains byte-preserved. The runnable JAR is the builder, verifier, generated-section index, and headless CPU reference renderer. The supplied source audit still identifies 269 external host-boundary classes, so this report does not mislabel the partial export as a complete Minecraft client.
