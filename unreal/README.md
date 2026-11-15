# DC-07 inspection station

The `DC07Inspection` source plugin adds a placeable actor for an Unreal Editor demonstration. Left-click equipment to display its function and highlight the connections you assign. Press **M** to play the maintenance Level Sequence. An equipment entry can also start the sequence on click.

The Blender GLB has been reimported and verified in Blender. This plugin has yet to be built or exercised in Unreal Editor.

## Set up in Unreal Engine 5.6

1. In a C++ Unreal project, copy `DC07Inspection/` into the project's `Plugins/` directory. Reopen the project and build the plugin. Enable it under **Edit > Plugins** if needed.
2. Create and save a level. Use **File > Import Into Level** with `assets/DC-07.glb` and an Interchange scene pipeline. Keep the equipment and cables as separate actors. Check that the rack top is approximately 61 × 98 cm and preserve the pivots for the doors, server tray, and cable arm.
3. Check for an imported Level Sequence containing the five transform tracks. If your pipeline only imports the meshes, create a Level Sequence and transfer the five animated transforms from the Blender timeline. Preserve the six-second duration and compare the stowed pose, the 105° hinges, the 53 cm service stop, and the closed pose with the source. Place the resulting **Level Sequence Actor** in the level and turn off autoplay.
4. Place a **DC07 Inspection Station** actor. Assign the Level Sequence Actor to **Maintenance Sequence**. Assign a camera that can see the equipment and an emissive material for the selection highlight.
5. Fill the **Equipment** array. Use visible mesh actors with query collision that blocks **Visibility**. If a mesh cannot be selected, give it simple query collision or configure its complex collision for the cursor trace.

| Target | Function displayed | Connections to highlight |
| --- | --- | --- |
| Switch face | Aggregates the rack's server network uplinks. | The six blue patch leads and patch-panel face. |
| Patch-panel face | Terminates and labels fixed network runs. | The six blue patch leads and switch face. |
| SRV-01 server face | Pull-out compute unit supported by rails during service. | Both rails and the amber cable-arm runs. Enable **Play Sequence on Click** for this entry. |

Run **Play in Editor**. Click each target and then empty space to check material restoration. Press **M** twice during one run and confirm the second press leaves the active sequence playing. Verify the door, tray, and cable-arm positions against the Blender reference.
