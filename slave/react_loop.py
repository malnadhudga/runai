import re
from collections import Counter

from crew.core.llm_client import LLMClient
from crew.core.prompts import SLAVE_SYSTEM_PROMPT
from crew.slave.scratchpad import Scratchpad


class ReActLoop:
    """Implements the Thought -> Action -> Observation loop for a slave agent."""

    def __init__(self, llm_client: LLMClient, scratchpad: Scratchpad, tools_dict: dict):
        self.llm_client = llm_client
        self.scratchpad = scratchpad
        self.tools_dict = tools_dict
        self.done = False
        self.stuck = False
        self.result: str | None = None
        self.failure_report: dict | None = None

    def parse_tool_call(self, llm_response: str) -> tuple[str, dict] | None:
        """Extract a TOOL/ARGS block from the LLM's text response.

        Returns:
            (tool_name, args_dict) or None if no valid tool call found.
        """
        tool_match = re.search(r"TOOL:\s*(\w+)", llm_response)
        if not tool_match:
            return None

        tool_name = tool_match.group(1)
        if tool_name not in self.tools_dict:
            return None

        args_match = re.search(r"ARGS:\s*\n(.*)", llm_response, re.DOTALL)
        if not args_match:
            return (tool_name, {})

        args_text = args_match.group(1)
        args = self._parse_args(args_text)
        return (tool_name, args)

    def _parse_args(self, args_text: str) -> dict:
        """Parse YAML-like key: value pairs, supporting block scalars with |."""
        args: dict[str, str] = {}
        lines = args_text.split("\n")
        current_key: str | None = None
        current_value_lines: list[str] = []
        block_indent: int | None = None

        for line in lines:
            top_level = re.match(r"^(\w+):\s?(.*)", line)
            if top_level:
                if current_key is not None:
                    args[current_key] = "\n".join(current_value_lines)
                current_key = top_level.group(1)
                value_part = top_level.group(2).strip()
                if value_part == "|":
                    current_value_lines = []
                    block_indent = None
                else:
                    current_value_lines = [value_part]
                    block_indent = None
            elif current_key is not None:
                if block_indent is None:
                    stripped = line.lstrip()
                    if stripped:
                        block_indent = len(line) - len(stripped)
                if block_indent is not None and len(line) >= block_indent:
                    current_value_lines.append(line[block_indent:])
                elif line.strip() == "":
                    current_value_lines.append("")
                else:
                    current_value_lines.append(line)

        if current_key is not None:
            args[current_key] = "\n".join(current_value_lines).rstrip("\n")

        return args

    def _get_recent_tool_errors(self, window: int = 5) -> list[str]:
        """Extract error strings from the last N tool result messages."""
        tool_results = [
            m["content"] for m in self.scratchpad.messages
            if m["role"] == "user" and m["content"].startswith("Tool result")
        ]
        errors = []
        for content in tool_results[-window:]:
            if "error:" in content.lower():
                errors.append(content)
        return errors

    def _detect_stuck(self) -> bool:
        """Check if the slave is stuck and should escalate.

        Returns True if any of:
          - Same error appeared 3+ times in the last 5 tool results
          - 5+ consecutive iterations with no new file written and no DONE
          - Used more than 10 iterations without finishing
        """
        recent_errors = self._get_recent_tool_errors(window=5)

        # repeated error check
        if len(recent_errors) >= 3:
            counts = Counter(recent_errors)
            if counts.most_common(1)[0][1] >= 3:
                return True

        # stalled: many iterations, no files, not done
        if self.scratchpad.iteration >= 5 and not self.scratchpad.files_written:
            return True

        # over 10 iterations is a strong signal
        if self.scratchpad.iteration > 10:
            return True

        return False

    def _build_failure_report(self) -> dict:
        """Build a structured report about why the slave got stuck."""
        errors = self._get_recent_tool_errors(window=10)
        assistant_msgs = [
            m["content"] for m in self.scratchpad.messages
            if m["role"] == "assistant"
        ]
        task = self.scratchpad.task
        return {
            "task_id": task.task_id if task else "unknown",
            "task_description": task.description if task else "unknown",
            "iterations_used": self.scratchpad.iteration,
            "errors": errors,
            "files_written": list(self.scratchpad.files_written),
            "last_attempts": assistant_msgs[-3:],
        }

    def step(self) -> None:
        """Run one THINK → ACT → OBSERVE cycle."""
        # THINK
        response = self.llm_client.chat(
            self.scratchpad.get_messages(),
            system=SLAVE_SYSTEM_PROMPT,
        )
        self.scratchpad.append_assistant(response)

        # check for DONE: or PARTIAL:
        for marker in ("DONE:", "PARTIAL:"):
            if marker in response:
                idx = response.index(marker)
                self.result = response[idx + len(marker):].strip()
                self.done = True
                return

        # ACT
        parsed = self.parse_tool_call(response)
        if parsed is None:
            self.scratchpad.append_user(
                "You must either call a tool using the TOOL:/ARGS: format "
                "or finish with DONE: followed by your summary."
            )
            self.scratchpad.increment()
            if self._detect_stuck():
                self.failure_report = self._build_failure_report()
                self.stuck = True
                self.done = True
            return

        tool_name, tool_args = parsed

        tool_fn = self.tools_dict[tool_name]
        try:
            tool_result = tool_fn(**tool_args)
        except Exception as e:
            tool_result = f"error: {e}"

        if tool_name == "write_file" and "filepath" in tool_args:
            filepath = tool_args["filepath"]
            if filepath not in self.scratchpad.files_written:
                self.scratchpad.files_written.append(filepath)

        # OBSERVE
        self.scratchpad.append_tool_result(tool_name, tool_result)
        self.scratchpad.increment()

        # check if stuck after observe
        if self._detect_stuck():
            self.failure_report = self._build_failure_report()
            self.stuck = True
            self.done = True

    def is_done(self) -> bool:
        """Check if the loop should stop."""
        return self.done or self.stuck or self.scratchpad.is_maxed_out()
