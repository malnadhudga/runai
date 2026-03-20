# runai

CLI for multi-agent AI coding: a planner breaks goals into tasks, workers execute them, output is reviewed and assembled.

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/malnadhudga/runai.git
cd runai
```

### 2. Install (one-time)

```bash
pip install -e .
```

The `runai` command is on your PATH after install.

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

---

## Configuration

Edit `.env` in the folder you run `runai` from:

```
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
```

---

## Docker

```bash
docker build -t runai .
docker run --env-file .env -it runai
```

Release tags (`v*.*.*`) build and push to Artifact Registry if GitHub Actions secrets are set — see `.github/workflows/release.yml`.
