Sky / cloud / weather / light export
====================================

Source checkout:
  D:\voxelworldshadersoruces\mcp940

This folder is a read-only study/export copy. The source checkout was not edited.

full-files/
  Focused Java implementation files and byte-for-byte copies of the six vanilla
  environment textures used by the sky, clouds, sun/moon and precipitation paths.

sections/
  Exact source sections extracted from mixed files. Each output file has labeled
  blocks; manifest.tsv records the original source path and exact inclusive line
  range for every block. Section extracts are text study files, not standalone
  compilable Java classes.

The exported path covers:
  - vanilla sky dome, End skybox, sunrise, sun, moon and stars;
  - fast and fancy clouds plus cloud animation/cache state;
  - fog and weather rendering;
  - client lightmap generation;
  - World/WorldProvider celestial and weather inputs;
  - SKY/BLOCK light propagation through World, Chunk and block storage;
  - OptiFine custom sky, custom colors and dynamic lights;
  - ShaderMod sky/cloud/weather/lightmap/shadow hooks.

Important distinction:
  assets/minecraft/shaders contains vanilla post-processing shader assets. The
  actual external shader-pack GLSL files are loaded at runtime by ShaderMod and
  are not present in this MCP source checkout.

Closure additions and captioned dependency snippets are documented in CLOSURE_ADDITIONS.txt and sections\closure-additions\.
