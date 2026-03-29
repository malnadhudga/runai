# runai

CLI for multi-agent AI coding: a planner breaks goals into tasks, workers execute them, output is reviewed and assembled.

---

## Installation

### Windows — one-liner install

Open **PowerShell** and run:

```powershell
irm https://raw.githubusercontent.com/malnadhudga/runai/main/install.ps1 | iex
```

This checks for Python, installs it via winget if missing, installs `runai`, and adds it to your PATH. Then just run `runai`.

### macOS / Linux

```bash
pip install runai
```

### From source (any platform)

```bash
git clone https://github.com/malnadhudga/runai.git
cd runai
pip install -e .
```

### 3. Add your API key

Copy `.env.example` to `.env` and set at least one key:

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

### 4. Run

```bash
runai
```

From a clone without global install, from repo root:

```bash
python -m runai.cli.main
# or (Unix)
chmod +x runai.sh && ./runai.sh
```

Interactive REPL opens. Type your goal and press Enter twice.

One-shot (single goal):

```bash
runai "write a hello world script"
```

---

## Usage

```
runai> Write server.py: HTTP server on port 8000...
```

Commands inside the REPL:

| Command | Description |
|---------|-------------|
| `/files` | List files in workspace/src/ |
| `/read <file>` | Show a file's contents |
| `/status` | Show last task table |
| `/model` | Show or switch model |
| `/clear` | Clear the terminal |
| `/quit` | Exit |

---

## Architecture

```
runai/
├── cli/          # Command-line interface
├── core/         # LLM client, task queue, prompts, context store
├── master/       # Orchestrator, planner, reviewer, assembler, dispatcher
├── slave/        # Autonomous coding agents & ReAct loop
└── tools/        # File I/O, code execution, agent communication

workspace/        # Working directory for agent outputs (repo root)
```

Planner, reviewer, assembler, slaves, and `ask_master` all call **`LLMClient.chat()`** only. There is no second path to Gemini: **`runai/core/llm_client.py`** either posts to **`RUNAI_GEMINI_PROXY_URL`** or calls Google’s SDK, so the rest of the pipeline stays the same. Gemini always uses **`gemini-2.5-flash-lite`** (`DEFAULT_GEMINI_MODEL` in `llm_client.py`).

---

## API keys: GitHub Secrets vs `pip install`

**GitHub Secrets** (e.g. `OPENAI_API_KEY` in repo **Settings → Secrets**) are only available **inside GitHub Actions** when a workflow runs. They are **not** baked into the package on PyPI. If they were, **everyone** who `pip install`s would get your key — that would be a security breach, and PyPI packages don’t work that way.

| Who | Where the LLM key comes from |
|-----|------------------------------|
| **Someone who `pip install runai`** | Their **own** keys for direct APIs, **or** your proxy (`RUNAI_GEMINI_PROXY_URL`) when they have **no** `GEMINI_API_KEY` (you bill via your server key). |
| **Your CI on GitHub** | **Secrets** you add to the repo; pass them into the job as `env:` (see below). |

So: **`pip install` users always bring their own keys** to call OpenAI/Gemini. They still **see the agent work in the terminal** (plans, tool calls, Rich output) — same as a clone — once their key is set.

### Optional: run a job on GitHub using your secret

Use this only for **automated smoke tests** or demos in Actions, not for end users:

```yaml
jobs:
  smoke:
    runs-on: ubuntu-latest
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install .
      - run: runai "say hello in one line"
```

Add `OPENAI_API_KEY` (or `GEMINI_API_KEY`) under **Settings → Secrets and variables → Actions → Secrets**. Prefer **`workflow_dispatch`** so it doesn’t run on every push and burn tokens.

---

## Configuration

Edit `.env` in the folder you run `runai` from:

```
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
RUNAI_GEMINI_PROXY_URL=
RUNAI_GEMINI_PROXY_TOKEN=
RUNAI_PROXY_CLIENT_ID=
```

### Gemini: local key vs proxy (current behavior)

- **`GEMINI_API_KEY` set** → client calls **Google directly**. `RUNAI_GEMINI_PROXY_URL` is **ignored** for Gemini (user’s key never hits your server).
- **`GEMINI_API_KEY` unset** and **`RUNAI_GEMINI_PROXY_URL` set** → every Gemini request is a `POST` to your proxy; your server calls Google with **your** platform key. (Forwarding the user’s key in the JSON body is **not** implemented for now.)
- Optional **`RUNAI_PROXY_CLIENT_ID`**: `client_id` + `X-Runai-Client-Id`. Optional **`RUNAI_GEMINI_PROXY_TOKEN`**: `Authorization: Bearer …`.

**Proxy contract** (`POST`, `Content-Type: application/json`):

```json
{
  "model": "gemini-2.5-flash-lite",
  "system": "optional system prompt",
  "messages": [{ "role": "user", "content": "..." }],
  "client_id": "optional-from-RUNAI_PROXY_CLIENT_ID"
}
```

Respond with JSON containing one string field: **`text`**, **`content`**, **`message`**, or **`response`** — or plain text body.

---

## Docker

```bash
docker build -t runai .
docker run --env-file .env -it runai
```

### Release to PyPI (tags `v*.*.*`)

Push a tag like `v0.1.1` after bumping **`version`** in `pyproject.toml`. **PyPI publish** runs on that tag; set GitHub secret **`PYPI_API_TOKEN`**.

Docker → **Google Artifact Registry** is **off** by default (`docker-build.yml` / `docker-push.yml` are manual / no-op). Re-enable those workflows if you want images in GCP again.
