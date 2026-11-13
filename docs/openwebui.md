# OpenWebUI integration

For the recommended Docker Desktop setup, follow **[docker-desktop.md](docker-desktop.md)**. It runs OpenWebUI, Ollama, LiteLLM, the Airender API, and headless Blender in one Compose project.

OpenWebUI is the conversational interface. You describe design changes in chat; the model can call the Airender OpenAPI tool. The JSON room brief remains an internal, reviewable source of truth and does not need to be edited by hand.

## Docker Desktop connection

After `docker compose up -d --build`, add this OpenAPI schema URL to OpenWebUI's Tools / OpenAPI Servers settings:

```
http://airender-api:8000/openapi.json
```

This is the internal Docker DNS address, not localhost. Enable the Airender Local tools for the `airender` model.

## Non-Docker / host-run API

If you run only the Airender API on the host, use the steps below instead of the Compose instructions.

Create and activate a virtual environment, then install the API dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\server\requirements.txt
```

Configure an OpenAI-compatible LiteLLM endpoint and run:

```powershell
$env:AIR_RENDER_LLM_BASE_URL = "http://127.0.0.1:4000/v1"
$env:AIR_RENDER_LLM_API_KEY = "your-local-litellm-key"
$env:AIR_RENDER_LLM_MODEL = "airender"
$env:BLENDER_EXE = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
uvicorn server.airender_api:app --host 127.0.0.1 --port 8765
```

For host-run OpenWebUI, add `http://127.0.0.1:8765/openapi.json` as the tool schema URL. For OpenWebUI running in Docker while the API runs on Windows, use `http://host.docker.internal:8765/openapi.json` and bind the API to a host-reachable interface; keep it firewalled from untrusted networks.

## Behaviour and safeguards

- Every successful spec update creates a timestamped backup in `config/`.
- Validation errors leave the current project unchanged.
- If Blender fails, the previous known-good spec is restored and the failed candidate is preserved for debugging.
- The endpoint only runs preview rendering. Final rendering remains a separately approved step.
- Treat example dimensions as illustrative until verified on site.
- This is a visualization prototype, not certified BIM or construction output.
