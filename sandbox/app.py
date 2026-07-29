"""AAP MCP chat sandbox — Gemini + remote AAP MCP toolsets."""

from __future__ import annotations

import json
import os
import secrets
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, Field

MCP_BASE = os.environ.get(
    "MCP_BASE_URL", "https://mcp.snnzx.gcp.redhatworkshops.io"
).rstrip("/")
AAP_MCP_TOKEN = os.environ.get("AAP_MCP_TOKEN", "")
SANDBOX_PASSWORD = os.environ.get("SANDBOX_PASSWORD", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)
GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "openenv-snnzx")
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Default: the aggregate /mcp endpoint exposes every AAP MCP tool (~100+).
# Set MCP_TOOLSETS=job_management,inventory_management,... to limit to curated subsets.
_raw_toolsets = os.environ.get("MCP_TOOLSETS", "mcp").strip()
TOOLSETS: list[tuple[str, str]] = []
for part in _raw_toolsets.split(","):
    path = part.strip().strip("/")
    if not path:
        continue
    # server label for Gemini function names
    label = "aap-mcp" if path == "mcp" else f"aap-{path.replace('_', '-')}"
    TOOLSETS.append((label, path))
if not TOOLSETS:
    TOOLSETS = [("aap-mcp", "mcp")]

SYSTEM_PROMPT = """You are an Ansible Automation Platform (AAP) operations assistant with Gemini AI capabilities.

- Prefer AAP MCP tools for jobs, inventories, users, projects, credentials, settings, and platform state.
- By default the sandbox loads the aggregate MCP endpoint (`/mcp`) so every AAP MCP tool is available.
- MCP is in read-write mode: you may list AND create/update/launch resources (groups, launches, cancels, etc.) when the user asks.
- For create/update tools, put fields under the tool's `requestBody` argument when the schema requires it.
- Use Google Search (and URL context when available) for public web research: Ansible/AAP docs, CVEs, best practices, release notes.
- Combine both when useful (for example: look up a job template via MCP, then search docs for how to configure it).
- Prefer tools over guessing. Be concise and accurate. Include names/IDs for AAP resources. Cite web sources briefly when you used search.
- Confirm destructive actions (cancel/delete) briefly before calling tools if the user intent is ambiguous.
"""

# Built-in Gemini tools (web + code). MCP function tools are merged at runtime.
ENABLE_GOOGLE_SEARCH = os.environ.get("ENABLE_GOOGLE_SEARCH", "true").lower() in (
    "1",
    "true",
    "yes",
)
ENABLE_CODE_EXECUTION = os.environ.get("ENABLE_CODE_EXECUTION", "true").lower() in (
    "1",
    "true",
    "yes",
)
ENABLE_URL_CONTEXT = os.environ.get("ENABLE_URL_CONTEXT", "true").lower() in (
    "1",
    "true",
    "yes",
)

app = FastAPI(title="AAP Gemini MCP Sandbox")
serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="aap-mcp-sandbox")

# In-memory chat histories keyed by session id (lab scale).
_histories: dict[str, list[types.Content]] = {}
_mcp_cache: dict[str, Any] = {"tools": None, "gemini_tools": None, "fetched_at": 0}


class LoginBody(BaseModel):
    password: str = Field(min_length=1)


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


def _cookie_name() -> str:
    return "aap_sandbox_session"


def _set_session(response: Response, email: str = "sandbox-user") -> str:
    sid = secrets.token_urlsafe(24)
    token = serializer.dumps({"sid": sid, "email": email, "ts": int(time.time())})
    response.set_cookie(
        _cookie_name(),
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    _histories.setdefault(sid, [])
    return sid


def _read_session(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(_cookie_name())
    if not raw:
        return None
    try:
        data = serializer.loads(raw, max_age=60 * 60 * 12)
        if not isinstance(data, dict) or "sid" not in data:
            return None
        return data
    except BadSignature:
        return None


def _require_user(request: Request) -> dict[str, Any]:
    user = _read_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user


async def _mcp_jsonrpc(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    session_id: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    headers = {
        "Authorization": f"Bearer {AAP_MCP_TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-03-26",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
    new_session = resp.headers.get("mcp-session-id") or session_id
    text = resp.text
    if resp.status_code >= 400:
        raise RuntimeError(f"MCP HTTP {resp.status_code}: {text[:300]}")
    # Streamable HTTP may return SSE or plain JSON.
    if "text/event-stream" in resp.headers.get("content-type", ""):
        data_line = None
        for line in text.splitlines():
            if line.startswith("data:"):
                data_line = line[5:].strip()
        if not data_line:
            raise RuntimeError(f"Empty SSE from MCP: {text[:200]}")
        return json.loads(data_line), new_session
    return resp.json(), new_session


async def _load_mcp_tools(force: bool = False) -> tuple[list[dict[str, Any]], list[types.Tool]]:
    now = time.time()
    if (
        not force
        and _mcp_cache["tools"] is not None
        and now - float(_mcp_cache["fetched_at"]) < 300
    ):
        return _mcp_cache["tools"], _mcp_cache["gemini_tools"]

    if not AAP_MCP_TOKEN:
        raise RuntimeError("AAP_MCP_TOKEN is not configured")

    declarations: list[types.FunctionDeclaration] = []
    catalog: list[dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        for server_name, path in TOOLSETS:
            # Aggregate endpoint is /mcp; curated toolsets are /{name}/mcp
            url = f"{MCP_BASE}/mcp" if path == "mcp" else f"{MCP_BASE}/{path}/mcp"
            init, session = await _mcp_jsonrpc(
                client,
                url,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "aap-mcp-sandbox", "version": "1.0"},
                    },
                },
            )
            # notifications/initialized is recommended but not required for AAP.
            listed, session = await _mcp_jsonrpc(
                client,
                url,
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                session_id=session,
            )
            tools = (listed.get("result") or {}).get("tools") or []
            for tool in tools:
                raw_name = tool["name"]
                # Gemini function names: [a-zA-Z_][a-zA-Z0-9_]* ; keep mapping.
                safe = f"{server_name.replace('-', '_')}__{raw_name}"
                safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in safe)
                catalog.append(
                    {
                        "safe_name": safe,
                        "mcp_name": raw_name,
                        "server": server_name,
                        "url": url,
                        "description": tool.get("description") or raw_name,
                        "input_schema": tool.get("inputSchema") or {"type": "object", "properties": {}},
                    }
                )
                declarations.append(
                    types.FunctionDeclaration(
                        name=safe,
                        description=f"[{server_name}] {tool.get('description') or raw_name}",
                        parameters_json_schema=tool.get("inputSchema")
                        or {"type": "object", "properties": {}},
                    )
                )

    gemini_tools = [types.Tool(function_declarations=declarations)] if declarations else []
    _mcp_cache.update({"tools": catalog, "gemini_tools": gemini_tools, "fetched_at": now})
    return catalog, gemini_tools


async def _call_mcp_tool(entry: dict[str, Any], arguments: dict[str, Any]) -> str:
    async with httpx.AsyncClient() as client:
        _, session = await _mcp_jsonrpc(
            client,
            entry["url"],
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "aap-mcp-sandbox", "version": "1.0"},
                },
            },
        )
        result, _ = await _mcp_jsonrpc(
            client,
            entry["url"],
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": entry["mcp_name"], "arguments": arguments or {}},
            },
            session_id=session,
        )
    return json.dumps(result.get("result", result), indent=2, default=str)[:120000]


def _genai_client() -> genai.Client:
    return genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)


def _builtin_gemini_tools() -> list[types.Tool]:
    """Optional built-in tools. Prefer Google Search; other builtins are opt-in.

    Vertex often rejects mixing Search/URL/code tools with custom function
    declarations in one request — callers should fall back to MCP-only.
    """
    tools: list[types.Tool] = []
    if ENABLE_GOOGLE_SEARCH and hasattr(types, "GoogleSearch"):
        tools.append(types.Tool(google_search=types.GoogleSearch()))
    # URL context / code execution are powerful but frequently incompatible with
    # simultaneous MCP function calling on Vertex — enable only when Search is off
    # or when MCP tools are empty.
    if not tools:
        if ENABLE_URL_CONTEXT and hasattr(types, "UrlContext"):
            try:
                tools.append(types.Tool(url_context=types.UrlContext()))
            except Exception:  # noqa: BLE001
                pass
        if ENABLE_CODE_EXECUTION:
            code_cls = getattr(types, "ToolCodeExecution", None) or getattr(
                types, "CodeExecution", None
            )
            if code_cls is not None:
                try:
                    tools.append(types.Tool(code_execution=code_cls()))
                except Exception:  # noqa: BLE001
                    pass
    return tools


def _tool_bundles(
    mcp_tools: list[types.Tool], user_message: str = ""
) -> list[list[types.Tool] | None]:
    """Ordered tool configurations to try (best match → safest)."""
    builtin = _builtin_gemini_tools()
    mcp = list(mcp_tools or [])
    text = (user_message or "").lower()
    wants_web = any(
        k in text
        for k in (
            "search the web",
            "google",
            "https://",
            "http://",
            "look up",
            "from the web",
            "online",
            "docs.redhat.com",
            "what is new",
            "cve",
            "release notes",
        )
    )
    bundles: list[list[types.Tool] | None] = []
    if wants_web:
        if builtin:
            bundles.append(builtin)
        if builtin and mcp:
            bundles.append(builtin + mcp)
        if mcp:
            bundles.append(mcp)
    else:
        if mcp:
            bundles.append(mcp)
        if builtin and mcp:
            bundles.append(builtin + mcp)
        if builtin:
            bundles.append(builtin)
    if not bundles:
        bundles.append(None)
    seen: set[str] = set()
    out: list[list[types.Tool] | None] = []
    for b in bundles:
        key = "none" if b is None else ",".join(
            sorted(
                {
                    (
                        "search"
                        if getattr(t, "google_search", None)
                        else "url"
                        if getattr(t, "url_context", None)
                        else "code"
                        if getattr(t, "code_execution", None)
                        else "fn"
                    )
                    for t in b
                }
            )
        ) + f":{len(b)}"
        if key in seen:
            continue
        seen.add(key)
        out.append(b)
    return out


async def _run_agent(sid: str, user_message: str) -> dict[str, Any]:
    catalog, mcp_tool_wrappers = await _load_mcp_tools()
    by_name = {t["safe_name"]: t for t in catalog}
    history = _histories.setdefault(sid, [])
    history.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    client = _genai_client()
    tool_trace: list[dict[str, Any]] = []
    final_text = ""
    bundles = _tool_bundles(mcp_tool_wrappers, user_message)
    tools = bundles[0]
    bundle_idx = 0

    for _ in range(8):
        response = None
        last_exc: Exception | None = None
        while bundle_idx < len(bundles):
            tools = bundles[bundle_idx]
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=tools,
                        temperature=0.2,
                    ),
                )
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                tool_trace.append(
                    {
                        "server": "gemini",
                        "tool": "tool_config_fallback",
                        "args": {"bundle": bundle_idx, "reason": str(exc)[:240]},
                    }
                )
                bundle_idx += 1
        if response is None:
            raise RuntimeError(f"Gemini generate_content failed: {last_exc}")

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content:
            final_text = "No response from model."
            break

        history.append(candidate.content)
        fn_calls = [
            p.function_call
            for p in (candidate.content.parts or [])
            if getattr(p, "function_call", None) and p.function_call.name
        ]
        text_parts = [
            p.text for p in (candidate.content.parts or []) if getattr(p, "text", None)
        ]
        if text_parts:
            final_text = "\n".join(text_parts)

        gm = getattr(candidate, "grounding_metadata", None)
        if gm is not None:
            tool_trace.append(
                {
                    "server": "gemini",
                    "tool": "google_search",
                    "args": {"grounded": True},
                }
            )

        if not fn_calls:
            break

        # Function calling requires MCP tools in the active bundle.
        if tools is not None and not any(
            getattr(t, "function_declarations", None) for t in tools
        ):
            # Switch to an MCP-capable bundle for the next turn.
            for i, b in enumerate(bundles):
                if b and any(getattr(t, "function_declarations", None) for t in b):
                    bundle_idx = i
                    break

        fn_response_parts: list[types.Part] = []
        for fc in fn_calls:
            entry = by_name.get(fc.name or "")
            args = dict(fc.args or {})
            if not entry:
                payload = json.dumps({"error": f"Unknown tool {fc.name}"})
            else:
                try:
                    payload = await _call_mcp_tool(entry, args)
                    tool_trace.append(
                        {
                            "server": entry["server"],
                            "tool": entry["mcp_name"],
                            "args": args,
                        }
                    )
                except Exception as exc:  # noqa: BLE001 — surface tool errors to model
                    payload = json.dumps({"error": str(exc)})
            fn_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name or "tool",
                    response={"result": payload},
                )
            )
        history.append(types.Content(role="user", parts=fn_response_parts))

    if len(history) > 40:
        _histories[sid] = history[-40:]

    return {"reply": final_text or "(empty)", "tools_used": tool_trace}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    user = _read_session(request)
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    authed = "true" if user else "false"
    email = (user or {}).get("email", "")
    html = html.replace("{{AUTHED}}", authed).replace("{{EMAIL}}", email)
    return HTMLResponse(html)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "mcp_base": MCP_BASE,
        "project": GCP_PROJECT,
        "model": GEMINI_MODEL,
        "password_login": bool(SANDBOX_PASSWORD),
        "google_search": ENABLE_GOOGLE_SEARCH,
        "url_context": ENABLE_URL_CONTEXT,
        "code_execution": ENABLE_CODE_EXECUTION,
    }


@app.post("/api/login")
async def login(body: LoginBody, response: Response) -> dict[str, Any]:
    if not SANDBOX_PASSWORD:
        raise HTTPException(status_code=500, detail="SANDBOX_PASSWORD not configured")
    if not secrets.compare_digest(body.password, SANDBOX_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid password")
    _set_session(response, email="sandbox-user")
    return {"ok": True, "email": "sandbox-user"}


@app.post("/api/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    user = _read_session(request)
    if user:
        _histories.pop(user["sid"], None)
    response.delete_cookie(_cookie_name())
    return {"ok": "true"}


@app.get("/api/me")
async def me(request: Request) -> dict[str, Any]:
    user = _require_user(request)
    return {"email": user.get("email"), "sid": user["sid"]}


@app.post("/api/chat")
async def chat(body: ChatBody, request: Request) -> JSONResponse:
    user = _require_user(request)
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    try:
        result = await _run_agent(user["sid"], body.message.strip())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(result)


@app.post("/api/reset")
async def reset(request: Request) -> dict[str, str]:
    user = _require_user(request)
    _histories[user["sid"]] = []
    return {"ok": "true"}


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
