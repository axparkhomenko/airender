# Airender on Docker Desktop (Windows)

This Compose stack runs the local model, OpenAI-compatible gateway, OpenWebUI,
Airender API, and headless Blender renderer.

## Services and ports

| Service | Host URL / port | Purpose |
|---|---|---|
| OpenWebUI | http://localhost:3334 | Chat interface |
| LiteLLM | http://localhost:4001 | OpenAI-compatible model gateway |
| Ollama | http://localhost:11435 | Local model runtime |
| Airender API | http://localhost:8765 | OpenAPI tool and project actions |

Host ports are configurable in .env. Containers communicate through Docker DNS
service names. Airender uses http://litellm:4000/v1; OpenWebUI uses the same
internal gateway. Host-side ports are loopback-only.

## 1. Prepare the project

1. Install and start Docker Desktop.
2. Ensure Docker Desktop is using Linux containers and the WSL 2 backend.
3. Clone this repository or pull the latest main branch.
4. Run the bootstrap script below. It creates a local .env with strong random
   secrets if one does not already exist. Keep .env private and do not commit it.

Recommended PowerShell bootstrap:

```powershell
.\scripts\start-docker.ps1
```

Or create the file manually:

```powershell
Copy-Item .env.example .env
notepad .env
```

## 2. Start the stack

From the repository root:

```powershell
docker compose up -d --build
```

First startup downloads the containers, builds the Airender image with Blender
5.2.3, and downloads qwen2.5:7b into the persistent Ollama volume. The model
download is several GB and may take time.

```powershell
docker compose ps
docker compose logs -f ollama-model-init
```

Open http://localhost:3334 and create the first OpenWebUI account. It becomes
the administrator.

## 3. Enable the Airender tool in OpenWebUI

In OpenWebUI go to **Settings → Admin → Integrations → External Tool Servers**.
Add a server, select **OpenAPI**, and configure:

- Server URL: `http://airender-api:8000`
- Spec path: `/openapi.json`

Verify the connection and save it. Enable the Airender tool server for the
chat. Available operations include:
- `airender_health`: check the API process.
- `blender_diagnostics`: run Blender's version check.
- `run_blender_smoke_test`: create a small test .blend file without touching
  the bedroom specification or starting a render.
- `get_project_spec`: read the current room brief.
- `apply_design_prompt`: update the room brief and render a preview.

Tool calls are made from the OpenWebUI backend, so the internal Docker DNS
address is correct. Do not replace it with localhost: inside a container,
localhost means that container itself.

### First Blender test from OpenWebUI

After enabling the tools, open a chat using the `airender` model and ask:

```text
Проверь доступность Blender через blender_diagnostics.
Если проверка успешна, вызови run_blender_smoke_test и создай тестовую сцену.
Не изменяй спецификацию спальни и не запускай рендер.
Сообщи точный путь к созданному .blend-файлу и его размер.
```

The expected file is `output/airender_blender_smoke_test.blend` in the
project folder on Windows. The smoke test creates a floor, cube, camera, and
light, saves the scene, and does not render. This is a technical test, not the
first architectural bedroom scene.

You can also check the file from PowerShell:

```powershell
Test-Path .\output\airender_blender_smoke_test.blend
Get-Item .\output\airender_blender_smoke_test.blend | Select-Object FullName, Length
```

### Reuse an existing OpenWebUI container

The Compose stack also starts its own OpenWebUI on port 3334, leaving port 3333
free for an existing installation. If you prefer to keep using your current
OpenWebUI container instead of the included one:

1. Start the Airender stack as usual.
2. Find the existing container name with `docker ps`.
3. Attach that container to the Airender network:

   ```powershell
   docker network connect airender-net <existing-open-webui-container>
   ```

4. In that existing OpenWebUI, add an OpenAI-compatible connection:
   - Base URL: `http://litellm:4000/v1`
   - API key: the value of `LITELLM_MASTER_KEY` from the project's local
     `.env` file.
5. Add the Airender OpenAPI tool server using the same internal URL and path
   listed above.

The existing container can then reach both services by Docker DNS without
exposing their internal ports to the LAN. You can stop only the bundled UI
with `docker compose stop open-webui`; this does not stop LiteLLM, Ollama,
or the Airender API.

Suggested model system prompt:

```text
You are the Airender architectural visualization assistant.
For a request to modify the current room, call Airender Local
apply_design_prompt with the user's natural-language instruction.
Do not ask the user to edit JSON. Ask a clarifying question when measurements,
orientation, or layout are ambiguous. Never claim an update or preview exists
unless the tool confirms success. Preview first; never initiate a final render
without explicit user approval. Distinguish visualization from construction BIM.
```

## 4. Check the services

```powershell
Invoke-RestMethod http://localhost:8765/health
Invoke-RestMethod http://localhost:8765/blender/diagnostics
Invoke-RestMethod http://localhost:8765/project/spec
Invoke-RestMethod http://localhost:4001/health/liveliness
docker compose logs --tail 100 airender-api litellm open-webui ollama
```

CPU-only model test through LiteLLM:

```powershell
$env:KEY = (Select-String '^LITELLM_MASTER_KEY=' .env).Line.Split('=',2)[1]
$body = @{
  model = "airender"
  messages = @(@{ role = "user"; content = "Reply with exactly: Airender model is ready." })
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri http://localhost:4001/v1/chat/completions -Headers @{ Authorization = "Bearer $env:KEY" } -ContentType "application/json" -Body $body
```

## 5. Useful commands

```powershell
docker compose up -d --build
docker compose down
docker compose logs -f
docker compose pull
docker compose up -d
```

Do not use `docker compose down -v` unless you intend to delete the
persistent Ollama model cache and OpenWebUI data.

## Model and hardware

Default model: `qwen2.5:7b`, exposed to OpenWebUI and Airender through
LiteLLM as `airender`. It is a starter model for instruction following,
JSON editing, and tool use. Performance depends on RAM/VRAM. The first pull
requires several GB of disk space.

If changing the model, update both the Ollama pull setting in
`docker-compose.yml` and the provider model in `litellm/config.yaml`.

CPU mode is the default. For NVIDIA acceleration under Docker Desktop, use
the WSL 2 backend and a supported NVIDIA driver, then run:

```powershell
docker compose -f docker-compose.yml -f docker-compose.nvidia.yml up -d --build
```

GPU passthrough depends on the host GPU, Windows driver, WSL 2, and Docker
Desktop versions. If Docker reports an unsupported GPU request, use the
default CPU Compose file. Verify GPU use in Ollama logs; do not assume it.

## Architecture and safety

- API and LiteLLM secrets remain in the local .env file.
- The API is published only on 127.0.0.1 on the host.
- OpenWebUI reaches the API over the private Compose network.
- The project directory is bind-mounted into Airender API, so backups, .blend
  files, and renders remain in the local repository folders.
- Ollama models and OpenWebUI data are stored in named Docker volumes.
- The API only runs preview rendering. Final rendering is not exposed.
- This is a visualization prototype, not certified BIM or construction output.
