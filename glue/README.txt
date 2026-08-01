MINECRAFT SKY/CLOUD/LIGHT HOST GLUE
=====================================

Purpose
-------
This folder is the host-dependency layer for the focused skybox, cloud, weather, lightmap, propagated SKY/BLOCK light and dynamic-light sources exported beside it. It is additive: the sibling full-files and sections folders remain the focused renderer source bundle.

How to read it
--------------
* full-files\\host contains exact source-file copies where the public contract or most of the class is needed (coordinates, state, resource managers, OpenGL wrappers, texture objects and dynamic-light entity support).
* sections\\existing contains exact copies of the earlier captioned sky/cloud/light sections.
* sections\\host-access contains new exact source ranges. Every range has NAME, SOURCE, SOURCE LINES, GOES TO, INPUT, OUTPUT / STATE CHANGES, CONSUMERS and WHY INCLUDED captions, followed by unchanged source text.
* external\\lwjgl contains the exact LWJGL jars and Windows native libraries used by the mcp940 1.12 client. These are binaries, not reconstructed source.
* manifest.tsv records every copied whole file, captioned range, contract note and external binary with SHA-256 hashes. Section rows also record a normalized source-range hash.

Subsystem path covered
-----------------------
Sky/cloud/weather: Minecraft -> World/WorldProvider/WorldInfo -> RenderGlobal/EntityRenderer -> GlStateManager/Tessellator/BufferBuilder -> LWJGL.
Static light: World -> Chunk -> ExtendedBlockStorage/NibbleArray -> IBlockState/Block/Material -> SKY/BLOCK and combined-light values.
Dynamic light: DynamicLights -> Entity/EntityLivingBase/EntityPlayer and fire/item subclasses -> ItemStack/Blocks/Items -> RenderGlobal/RenderChunk invalidation.
Resource path: Minecraft -> IResourceManager/ResourcePackRepository -> TextureManager/TextureUtil/SimpleTexture/DynamicTexture -> sky/weather/lightmap textures.

Boundary
--------
This is a source-level host closure, not a standalone Java/Minecraft build. Large generic renderer/entity classes are represented by exact host sections where only a subsystem contract is needed; unrelated Minecraft gameplay/render classes and third-party libraries remain host boundaries. Copying LWJGL binaries does not create a display context or the rest of the Minecraft runtime.
No compilation, shader validation or game launch was performed by this export. The audit is static and hash/range based.
