"""Local OpenWebUI-to-Blender bridge for Airender.

Run on localhost. The LLM returns a complete room-spec JSON document; this
service validates it, backs up the previous spec, and optionally renders only
the preview. It never runs final-quality rendering.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "config" / "bedroom_neoclassical.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate_spec.py"
BUILDER_PATH = ROOT / "scripts" / "build_bedroom.py"
OUTPUT_DIR = ROOT / "output"

LLM_BASE_URL = os.getenv("AIR_RENDER_LLM_BASE_URL", "http://127.0.0.1:4000/v1").rstrip("/")
LLM_API_KEY = os.getenv("AIR_RENDER_LLM_API_KEY", "local-dev")
LLM_MODEL = os.getenv("AIR_RENDER_LLM_MODEL", "")
BLENDER_EXE = os.getenv("BLENDER_EXE", "blender")
REQUEST_TIMEOUT = int(os.getenv("AIR_RENDER_TIMEOUT_SECONDS", "1800"))

app = FastAPI(
    title="Airender Local API",
    description="Natural-language room design updates for the local Blender scene.",
    version="0.1.0",
)


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=12000, description="Natural-language design instruction.")
    render_preview: bool = Field(default=True, description="Build the scene and render preview images. Final rendering is not available through this endpoint.")


def load_spec() -> dict[str, Any]:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cannot read current project spec: {exc}") from exc


def ask_model(user_prompt: str, current_spec: dict[str, Any]) -> dict[str, Any]:
    if not LLM_MODEL:
        raise HTTPException(
            status_code=503,
            detail="AIR_RENDER_LLM_MODEL is not configured. Set it to the model name exposed by your OpenAI-compatible endpoint.",
        )

    system = """You are the design-brief editor for Airender, a local architectural-visualization project.
Return ONLY one valid JSON object: the complete updated room specification, not a patch and not Markdown.
Use the supplied current specification as the source of truth.
Rules:
- Preserve all existing measurements, coordinates, openings, furniture positions, and camera settings unless the user explicitly asks to change them.
- Never invent site measurements. If a requested change needs unknown dimensions, preserve existing values and add a concise entry to a top-level design_notes array describing the assumption or missing information.
- Keep units as millimetres and preserve the existing coordinate convention.
- Preserve all required existing keys and nested structures. Change only what the user requested.
- Do not add executable code, scripts, shell commands, or arbitrary file paths.
- Do not claim construction/code compliance.
- If the request is ambiguous, preserve geometry and record the ambiguity in design_notes.
- Output strict JSON only."""

    payload = {
        "model": LLM_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": "CURRENT SPECIFICATION:\n" + json.dumps(current_spec, ensure_ascii=False) + "\n\nDESIGN REQUEST:\n" + user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        LLM_BASE_URL + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + LLM_API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        updated = json.loads(content)
        if not isinstance(updated, dict):
            raise ValueError("Model response is not a JSON object")
        return updated
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-3000:]
        raise HTTPException(status_code=502, detail=f"LLM endpoint returned HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not obtain valid JSON from the LLM endpoint: {exc}") from exc


def validate_spec(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    import importlib.util
    module_spec = importlib.util.spec_from_file_location("airender_validator", VALIDATOR_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec and module_spec.loader
    module_spec.loader.exec_module(module)
    return module.validate(spec)


def run_preview() -> dict[str, Any]:
    command = [
        BLENDER_EXE, "--background", "--python", str(BUILDER_PATH), "--",
        "--spec", str(SPEC_PATH), "--output", str(OUTPUT_DIR),
    ]
    try:
        completed = subprocess.run(
            command, cwd=str(ROOT), capture_output=True, text=True,
            timeout=REQUEST_TIMEOUT, check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Blender executable not found: {BLENDER_EXE}. Set BLENDER_EXE to blender.exe.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"Blender preview timed out after {REQUEST_TIMEOUT} seconds.") from exc

    log = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if completed.returncode != 0:
        raise HTTPException(status_code=500, detail={
            "message": "Blender preview failed. The previous specification has been restored.",
            "return_code": completed.returncode,
            "log_tail": log[-12000:],
        })
    return {"return_code": completed.returncode, "log_tail": log[-6000:]}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "project": str(ROOT),
        "llm_configured": bool(LLM_MODEL),
        "llm_base_url": LLM_BASE_URL,
        "llm_model": LLM_MODEL or None,
        "blender_executable": BLENDER_EXE,
    }


@app.get("/project/spec")
def get_project_spec():
    return load_spec()


@app.post("/prompt")
def apply_design_prompt(request: PromptRequest):
    """Interpret a natural-language design request, update the brief, and render preview."""
    current = load_spec()
    candidate = ask_model(request.prompt, current)
    errors, warnings = validate_spec(candidate)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Generated specification failed validation; current project was not changed.", "errors": errors, "warnings": warnings})

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = SPEC_PATH.with_name(SPEC_PATH.stem + f".backup-{stamp}.json")
    shutil.copy2(SPEC_PATH, backup)
    temporary = SPEC_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(SPEC_PATH)

    render_result = None
    if request.render_preview:
        try:
            render_result = run_preview()
        except HTTPException:
            failed = SPEC_PATH.with_name(SPEC_PATH.stem + f".failed-{stamp}.json")
            shutil.copy2(SPEC_PATH, failed)
            shutil.copy2(backup, SPEC_PATH)
            raise

    return {
        "status": "updated",
        "message": "Project specification updated.",
        "backup": str(backup.relative_to(ROOT)),
        "warnings": warnings,
        "design_notes": candidate.get("design_notes", []),
        "preview": render_result,
        "preview_directory": str((OUTPUT_DIR / "preview").relative_to(ROOT)) if request.render_preview else None,
        "final_render": "not_started",
    }
