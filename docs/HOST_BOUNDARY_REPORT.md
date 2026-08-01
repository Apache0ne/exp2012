# Archived-source host-boundary compile probe

A separate direct `javac` probe was run over all 123 Java files in `build/assembled-src/`, with the three supplied LWJGL JARs on the classpath.

```text
javac --release 8 -proc:none -Xmaxerrs 50 \
  -cp <supplied-lwjgl-jars> \
  -d build/archive-compile-probe \
  @build/archive-sources.list
```

## Result

**Expected host-boundary failure**

- Assembled archived Java files submitted: 123
- First-error cap: 50
- Errors reached before cap: 50
- First absent package: `net.minecraft.init`
- First absent classes: `net.minecraft.init.SoundEvents` and `net.minecraft.util.SoundEvent`
- Supplied dependency audit: 269 external host classes

This is not treated as a builder failure. The ZIP is a source closure around sky/cloud/weather/light/OptiFine/ShaderMod code, not a complete MCP 9.40 source tree. Generating empty stand-ins would make `javac` appear successful while breaking actual behavior and violating source preservation.

The verified PASS applies to the source-closure builder, manifest/hash verifier, generated Java section descriptors, registry, reproducible JAR, and headless CPU reference renderer. The assembled original source is ready to overlay onto the complete MCP 9.40 host workspace, where those external classes belong.
