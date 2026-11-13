# OpenWebUI integration

OpenWebUI is the conversational interface for Airender. You describe design changes in chat; the connected model calls the Airender OpenAPI tool. The local API asks the configured OpenAI-compatible model to update the internal room brief, validates it, makes a timestamped backup, and runs a Blender preview only.

## Architecture

OpenWebUI chat → connected model → Airender OpenAPI tool → local Airender API → validated JSON brief → Blender preview → output/preview.

The JSON remains the machine-readable source of truth, but normal use does not require editing it by hand. The API never exposes a final-render action.

## 1. Start the Airender API on Windows

From the repository root, create a virtual environment and install the API dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\server\requirements.txt
```

Configure the environment variables from server/.env.example in your terminal or as Windows environment variables. Example:

```powershell
$env:AIR_RENDER_LLM_BASE_URL = "http://127.0.0.1:4000/v1"
$env:AIR_RENDER_LLM_API_KEY = "local-dev"
$env:AIR_RENDER_LLM_MODEL = "your-model-name"
$env:BLENDER_EXE = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
uvicorn server.airender_api:app --host 127.0.0.1 --port 8765
```

Use the actual model name and endpoint exposed by your LiteLLM/Ollama/OpenAI-compatible service. The endpoint must support /chat/completions; JSON-object response mode is requested. If your provider does not support that mode, adjust the request in server/airender_api.py to use its supported structured-output format.

Check the service:
- http://127.0.0.1:8765/health
- http://127.0.0.1:8765/openapi.json

## 2. Connect it to OpenWebUI

In OpenWebUI, add an OpenAPI tool server using this schema URL:

```
http://127.0.0.1:8765/openapi.json
```

Give the tool a name such as Airender Local. Enable that tool for the model you use in chat. The operations are:
- apply_design_prompt: send a natural-language design instruction; by default it updates the brief and generates preview renders.
- get_project_spec: inspect the current structured brief.
- health_health_get (operation naming may vary in the UI): check service configuration.

If OpenWebUI runs in Docker, 127.0.0.1 inside its container is not the Windows host. Use a host-reachable address such as http://host.docker.internal:8765/openapi.json where supported, and make the API listen on an interface reachable from that container. Do not expose this unauthenticated development API to the public internet.

## 3. Suggested model system prompt in OpenWebUI

```text
You are the Airender architectural visualization assistant.
When the user asks to change the current room design, call the Airender Local apply_design_prompt tool with the user's request in natural language.
Do not ask the user to edit JSON. Ask clarifying questions when measurements, layout, or orientation are ambiguous.
Never claim a preview exists unless the tool confirms success.
Preview first; never initiate a final render without explicit user approval.
Distinguish visualization from construction-ready BIM.
```

## 4. Example chat prompts

- Сделай стены на полтона теплее, а латунь менее жёлтой. Геометрию не меняй.
- Покажи вариант с оливковыми акцентами вместо пыльно-голубых.
- Добавь мягкую подсветку гардеробной, но не меняй расположение перегородки.
- Перед рендером перечисли все изменения и предупреждения.

## Behaviour and safeguards

- The service binds to localhost in the documented setup.
- Every successful spec update creates a timestamped backup in config/.
- Validation errors leave the current project unchanged.
- If Blender fails, the previous known-good spec is restored; the failed candidate is preserved separately for debugging.
- The endpoint only runs the preview workflow. Final rendering remains a manual, separately approved step.
- Treat dimensions from the example as illustrative until verified on site.
- This is a visualization prototype, not certified BIM or construction output.
