# Airender architecture and local setup

## Intended flow

```text
Room brief (JSON + reference images)
          |
          v
Local orchestration agent (MCP-capable client / local LLM)
          |
          +----> Blender Python API: scene generation, materials, cameras, preview/final renders
          |
          +----> Optional FreeCAD/Bonsai + IfcOpenShell: BIM/IFC authoring and exchange
          |
          +----> Optional validation scripts: dimensions, clearances, object naming, deliverable checks
          |
          v
Review package: .blend + PNG previews/finals + JSON brief + validation report
```

The Blender scene builder is the runnable baseline. FreeCAD/BIM is an optional parallel authoring and documentation stage; this repository does not assume that an arbitrary FreeCAD MCP package exposes a stable command or export API.

## Windows setup

1. Install Blender 4.x (4.2 LTS is a practical baseline).
2. Clone the repository to a local workspace, e.g. `C:\\Projects\\airender`.
3. Open PowerShell in the repository.
4. Run the builder in Blender's bundled Python:

   ```powershell
   blender --background --python .\\scripts\\build_bedroom.py -- --spec .\\config\\bedroom_neoclassical.json --output .\\output
   ```

5. Review the preview images. Final renders are opt-in:

   ```powershell
   blender --background --python .\\scripts\\build_bedroom.py -- --spec .\\config\\bedroom_neoclassical.json --output .\\output --final
   ```

If the `blender` executable is not on PATH, replace it with the full path to `blender.exe`.

## MCP client configuration

Use the example in `config/mcp.example.json` as a *shape/template*, not a guaranteed drop-in configuration. MCP clients differ in how they launch local servers. The Blender addon must be installed and its listener started before a client can call it. Likewise, a FreeCAD MCP server may be an addon, a separate Python process, or an RPC bridge; follow the exact upstream version's installation instructions.

Do not expose an MCP listener to a public network. Bind local-only services to loopback where supported. Avoid passing client/project files to hosted LLM endpoints unless the project owner explicitly approves it.

## Geometry and unit contract

- Room brief: millimetres.
- Blender scene: metres.
- Z points up.
- The room origin is the south-west interior floor corner.
- Object names are stable identifiers and should be preserved when exporting or handing off to BIM.

The sample brief uses a 4.2 m × 5.4 m room, 3.1 m ceiling, and wardrobe zone beginning at Y=4.0 m. These values are sample inputs, not surveyed facts. The bedroom/wardrobe zoning and furniture clearances must be reviewed against actual site measurements.

## Quality gates

### Gate A — brief validation
- Units and coordinate convention are explicit.
- All dimensions are positive.
- Openings fit within their host walls.
- Door/window elevations do not exceed ceiling height.
- Furniture bounds remain inside the room.

### Gate B — visual review
- Check room shell, window, partition, furniture and camera framing in clay preview.
- Review circulation clearances and door swings.
- Confirm materials, mural placement, light balance, reflections and verticals.

### Gate C — construction/BIM handoff
A render is not a technical drawing. If construction deliverables are required, create and independently validate:
- dimensioned plans, elevations, sections and detail sheets;
- IFC classifications and property sets;
- door/window schedules and quantity takeoffs;
- clash checks and jurisdiction-specific code checks;
- structural design and engineering calculations.

Do not allow an LLM to invent or silently resolve missing dimensions. Ask for confirmation and preserve unknowns as unresolved fields.

## Known limitations of the first sample builder

- Window opening is assembled from wall segments for visualization; the script does not generate a full architectural wall object with parametric opening history.
- Furniture is a blockout, not a manufacturer-ready specification.
- The mural is an original procedural graphic with a stylised botanical look, not a high-fidelity hand-painted reproduction.
- GPU availability depends on the local Blender build and drivers; CPU rendering may be needed.
- Final camera composition and all clearances require human review.
