import json
import re

from crew.core.llm_client import LLMClient
from crew.core.prompts import FAILURE_ANALYSIS_PROMPT
from crew.tools.read_file import read_file


class FailureHandler:
    """Analyzes slave failures and decides the recovery strategy."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze(self, failure_report: dict, context: str) -> dict:
        """Ask the master LLM to decide how to recover from a stuck slave.

        Args:
            failure_report: Structured report from the stuck slave.
            context: Summary of completed tasks from ContextStore.

        Returns:
            Dict with decision, reason, and payload.
        """
        file_contents = {}
        for name in failure_report.get("files_written", []):
            content = read_file(name)
            if not content.startswith("error:"):
                file_contents[name] = content

        files_section = ""
        for name, content in file_contents.items():
            files_section += f"\n--- {name} ---\n{content}\n"

        errors_section = "\n".join(failure_report.get("errors", [])) or "None"
        attempts_section = "\n---\n".join(failure_report.get("last_attempts", []))

        user_message = (
            f"TASK DESCRIPTION:\n{failure_report.get('task_description', 'unknown')}\n\n"
            f"ITERATIONS USED: {failure_report.get('iterations_used', 0)}\n\n"
            f"ERRORS ENCOUNTERED:\n{errors_section}\n\n"
            f"LAST 3 AGENT ATTEMPTS:\n{attempts_section}\n\n"
            f"FILES WRITTEN:{files_section or ' None'}\n\n"
            f"CONTEXT FROM OTHER TASKS:\n{context or 'None'}\n"
        )

        response = self.llm_client.chat(
            [{"role": "user", "content": user_message}],
            system=FAILURE_ANALYSIS_PROMPT,
        )

        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict:
        """Parse the structured DECISION/REASON/PAYLOAD response."""
        decision_match = re.search(r"DECISION:\s*(\w+)", response)
        reason_match = re.search(r"REASON:\s*(.+?)(?:\n|$)", response)
        payload_match = re.search(r"PAYLOAD:\s*\n?(.*)", response, re.DOTALL)

        if not decision_match:
            return {
                "decision": "REWRITE",
                "reason": "Could not parse recovery response",
                "payload": response,
            }

        decision = decision_match.group(1).upper()
        if decision not in ("GUIDE", "SPLIT", "REWRITE", "ABORT"):
            decision = "REWRITE"

        reason = reason_match.group(1).strip() if reason_match else "No reason given"
        raw_payload = payload_match.group(1).strip() if payload_match else ""

        if decision == "SPLIT":
            raw_payload = self._strip_fences(raw_payload)
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                return {
                    "decision": "REWRITE",
                    "reason": "SPLIT payload was not valid JSON, falling back to rewrite",
                    "payload": raw_payload,
                }
        elif decision == "ABORT":
            payload = "none"
        else:
            payload = raw_payload

        return {
            "decision": decision,
            "reason": reason,
            "payload": payload,
        }

    @staticmethod
    def _strip_fences(text: str) -> str:
        m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()
