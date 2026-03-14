# crew

A CLI tool that runs a crew of GPT-based coding agents.

Crew uses a master/slave architecture where a planner breaks down user goals
into atomic subtasks, dispatches them to autonomous coding agents, reviews
their output, and assembles a final result.

## Installation

```bash
pip install -e .
```

## Usage

```bash
crew
```

Or run directly:

```bash
python -m crew.cli.main
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
