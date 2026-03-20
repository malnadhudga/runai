# crew

A CLI tool that runs a crew of GPT-based coding agents.

Crew uses a master/slave architecture where a planner breaks down user goals
into atomic subtasks, dispatches them to autonomous coding agents, reviews
their output, and assembles a final result.

## New user setup

1. **Clone or download the repo** and open a terminal in the project folder.

2. **Use Python 3.10+** (check with `python --version` or `python3 --version`).

3. **Install the project** (recommended: use a virtualenv first):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Linux / macOS
   pip install -e .
   ```

4. **Configure API keys.** Copy `.env.example` to `.env` and add at least one key:
   ```bash
   # Windows
   copy .env.example .env
   # Linux / macOS
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `GEMINI_API_KEY=...` and/or  
   - `OPENAI_API_KEY=...`

5. **Run crew** from the project folder:
   - **Windows:** `.\crew.bat` or `python crew`
   - **Linux / macOS:** `python crew` or `./crew` (after `chmod +x crew`)
   - Or, if the pip `crew` script is on your PATH: `crew`

   One-shot (single goal):  
   `.\crew.bat "write a hello world script"` or `python crew "write a hello world script"`  
   Interactive REPL (type goals and use `/files`, `/read`, `/quit`, etc.):  
   `.\crew.bat` or `python crew` with no arguments.

## Installation (reference)

```bash
pip install -e .
```

## Usage

```bash
crew
```

Or from the project root without needing `crew` on PATH:

```bash
python crew          # interactive REPL
python crew "goal"   # one-shot
.\crew.bat           # Windows interactive
.\crew.bat "goal"    # Windows one-shot
```

## Architecture

```
crew/
├── cli/          # Command-line interface & setup
├── core/         # LLM client, task queue, prompts, context store
├── master/       # Orchestrator, planner, reviewer, assembler, dispatcher
├── slave/        # Autonomous coding agents & ReAct loop
├── tools/        # File I/O, code execution, agent communication
└── workspace/    # Working directory for agent outputs
```

## Configuration

Copy `.env.example` to `.env` and set your API keys:

```bash
OPENAI_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
```

## Docker

```bash
docker build -t crew .
docker run --env-file .env -it crew
```
