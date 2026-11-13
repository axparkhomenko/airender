# Airender — Local Architectural Visualization Pipeline

A Windows-first architectural-visualization starter project. Describe room
changes in OpenWebUI; a local LLM updates the internal room brief, validates
it, and drives a headless Blender preview build.

## What the project includes

- OpenWebUI chat as the natural-language project interface.
- Ollama running a local Qwen model.
- LiteLLM as the OpenAI-compatible gateway shared by OpenWebUI and Airender.
- A FastAPI service that converts a prompt into an updated room brief, validates
  it, makes a timestamped backup, and runs preview rendering.
- Blender 5.2.3 in a Linux container for headless scene generation.
- Procedural materials and details: oak herringbone parquet, boiserie frames,
  fluted glass, warm LED coves, brass sconces, and a chinoiserie-inspired mural.
- A sample modern-neoclassical bedroom with wardrobe zone and three cameras.

## Quick start — Docker Desktop on Windows

1. Install and start Docker Desktop with the WSL 2 backend and Linux containers.
2. Clone this repository.
3. Open PowerShell in the repository root.
4. Run:

   ```powershell
   .\scripts\start-docker.ps1
   ```

   The script creates a local `.env` with fresh secrets if one does not
   already exist, then builds and starts the Compose stack.
5. Wait for the first model download (qwen2.5:7b; several GB).
6. Open [http://localhost:3334](http://localhost:3334) and create the first
   OpenWebUI administrator account.
7. In OpenWebUI, go to **Settings → Admin → Integrations → External Tool
   Servers**, add an **OpenAPI** server:
   - Server URL: `http://airender-api:8000`
   - Spec path: `/openapi.json`
8. Verify and save the tool server, then enable its tools in your chat.

Full instructions, health checks, port changes, and optional NVIDIA setup:
[docs/docker-desktop.md](docs/docker-desktop.md).

## Docker services

| Service | URL from Windows host | Role |
|---|---|---|
| OpenWebUI | http://localhost:3334 | Chat UI |
| LiteLLM | http://localhost:4001 | OpenAI-compatible gateway |
| Ollama | http://localhost:11435 | Local inference |
| Airender API | http://localhost:8765 | Project tools and preview workflow |

The containers use Docker DNS names to reach each other. For example, the
Airender API calls LiteLLM at `http://litellm:4000/v1`. Do not replace internal
container URLs with localhost.

Useful commands:

```powershell
docker compose ps
docker compose logs -f
docker compose down
docker compose up -d --build
```

Do not run `docker compose down -v` unless you intend to delete the Ollama
model cache and OpenWebUI chat/account data.

## Project structure

```text
config/
  bedroom_neoclassical.json
  mcp.example.json
docs/
  architecture.md
  docker-desktop.md
  openwebui.md
litellm/
  config.yaml
server/
  airender_api.py
  requirements.txt
scripts/
  archviz_generators.py
  build_bedroom.py
  validate_spec.py
  start-docker.ps1
Dockerfile
docker-compose.yml
docker-compose.nvidia.yml
.env.example
```

## Model

Default Ollama model: `qwen2.5:7b`, exposed by LiteLLM under the model name
`airender`. It is the initial local baseline for prompt interpretation,
JSON editing, and tool calling. Model speed depends on available system
memory and hardware. To change models, update the pull setting in
`docker-compose.yml` and the provider model in `litellm/config.yaml`.

CPU mode is the default. Optional NVIDIA configuration is documented in
[docs/docker-desktop.md](docs/docker-desktop.md).

## Manual / developer workflow

The JSON room brief remains the internal source of truth, but normal design
changes should be requested through OpenWebUI rather than editing it directly.
For developer-level work, the Blender builder can still be run manually:

```powershell
blender --background --python .\scripts\build_bedroom.py -- --spec .\config\bedroom_neoclassical.json --output .\output
```

Run validation independently:

```powershell
python .\scripts\validate_spec.py .\config\bedroom_neoclassical.json
```

Final rendering is deliberately not triggered by the chat API. Use the
separate manual `--final` workflow only after reviewing the preview.

## Coordinate convention

- JSON dimensions are millimetres; Blender scene coordinates are metres.
- X = room width, Y = room length, Z = up.
- Room origin is the south-west floor corner.
- Main sleeping zone occupies Y=0..4.0 m; wardrobe zone occupies Y=4.0..5.4 m.
- Confirm every opening, furniture clearance, and the bed/headboard orientation
  against measured drawings before use.

## Scope and limitations

This is an interior visualization workflow, not certified BIM or construction
documentation. It does not calculate structural adequacy, certify code
compliance, produce signed/stamped drawings, or replace a licensed architect
or engineer. Treat example dimensions as illustrative until verified on site.
For IFC, schedules, dimensioned plans/sections, and clash checking, integrate
and validate a dedicated BIM toolchain separately.

## MCP integration

See [docs/architecture.md](docs/architecture.md) and
[prompts/agent_system.md](prompts/agent_system.md). MCP server launch commands
are not hard-coded as universal truths because addon versions and clients vary.

## License

No license has been selected yet. Add a license after deciding how the project
should be reused.
