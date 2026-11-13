# Airender — Local Architectural Visualization Pipeline

A Windows-first, open-source starter project for turning a structured room brief into a parametric-ish Blender scene and client-ready architectural renders. The first reference workflow is a modern-neoclassical bedroom with a walk-in wardrobe.

## What this repository does

- Builds a named, dimensioned interior scene in Blender using Python and metric units.
- Generates reusable materials and details: oak herringbone parquet, boiserie frames, fluted glass, warm LED coves, brass sconces, and a procedural chinoiserie-inspired mural.
- Creates three architectural cameras and renders a clay preview before a final image pass.
- Keeps the room brief in JSON so dimensions and design intent are reviewable and versionable.
- Documents optional FreeCAD/BIM and MCP integration points.

## What it does not claim to do

This starter is an **interior visualization workflow**, not a certified construction-documentation system. It does not calculate structural adequacy, certify code compliance, produce signed/stamped drawings, or replace review by a licensed architect/engineer. A Blender render is not a construction drawing. For BIM/IFC schedules, dimensioned plans/sections, clash checking, and jurisdiction-specific code checks, integrate and validate a dedicated BIM toolchain (for example FreeCAD/Bonsai + IfcOpenShell) as a separate stage.

## Repository layout

```text
config/
  bedroom_neoclassical.json     # Editable room brief (millimetres)
  mcp.example.json              # Client-neutral MCP configuration example
docs/
  architecture.md               # Pipeline boundaries and setup notes
prompts/
  agent_system.md               # Agent operating rules and starter prompt
scripts/
  archviz_generators.py         # Reusable Blender material/detail generators
  build_bedroom.py              # Builds the example room and renders preview/final
```

## Requirements

- Windows 10/11 (paths in examples use Windows conventions)
- Blender 4.x (4.2 LTS recommended)
- Optional: FreeCAD 1.0+ and a compatible FreeCAD MCP addon/server
- Optional: OpenWebUI and a locally hosted OpenAI-compatible model endpoint (LiteLLM/Ollama)

The Blender scripts use Blender's bundled Python API and Python standard library only. No pip install is required for the scene-generation scripts.

## Quick start

1. Install Blender 4.x.
2. Clone this repository.
3. Edit `config/bedroom_neoclassical.json` to match the measured room. Treat measurements from the example as illustrative until verified on site.
4. Open Blender, switch to the Scripting workspace, and run:

   ```python
   exec(compile(open(r"path\\to\\airender\\scripts\\build_bedroom.py", encoding="utf-8").read(),
                "build_bedroom.py", "exec"))
   ```

   Or run Blender in background mode:

   ```powershell
   & "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" --background --python .\\scripts\\build_bedroom.py -- --spec .\\config\\bedroom_neoclassical.json --output .\\output
   ```

5. Inspect the clay preview images in `output/preview`. Change the JSON or layout code and rerun until the geometry and camera composition are approved.
7. For final rendering, run with `--final`:

   ```powershell
   blender --background --python .\\scripts\\build_bedroom.py -- --spec .\\config\\bedroom_neoclassical.json --output .\\output --final
   ```

The script saves a `.blend` scene and PNG renders. The exact output paths are printed in the Blender console.

## Coordinate convention

- JSON dimensions are millimetres.
- Blender scene coordinates are metres.
- X = room width, Y = room length, Z = up.
- Room origin is the south-west floor corner.
- Main sleeping zone occupies Y=0..4.0 m; wardrobe zone occupies Y=4.0..5.4 m.
- Wall and opening placements are generated from the JSON brief. Confirm every opening and furniture clearance against measured drawings before use.

## Render stages

- Preview: clay materials, low resolution, 64 samples.
- Final: Cycles, GPU when available (CPU fallback), OpenImageDenoise, AgX, 320 samples by default.
- Cameras: 24 mm hero, 28 mm vanity/wardrobe, 35 mm detail. Camera framing is generated from scene bounds and can be adjusted.

## MCP integration

See [docs/architecture.md](docs/architecture.md) and [prompts/agent_system.md](prompts/agent_system.md). MCP server launch commands are intentionally not hard-coded as universal truths: addon versions and MCP clients differ. Configure the actual installed FreeCAD/Blender server entry points using their current upstream instructions.

## Safety and production workflow

1. Verify measured dimensions and levels.
2. Generate geometry.
3. Review preview renders and clearances.
4. If construction output is needed, export to a BIM/CAD application and validate dimensions, classifications, schedules, and code requirements independently.
5. Obtain professional review before construction or procurement.

## License

No license has been selected yet. Add a license after deciding how you want this repository to be reused.
