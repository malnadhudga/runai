import os

from dotenv import load_dotenv

load_dotenv()

from crew.core.llm_client import LLMClient
from crew.core.task_queue import TaskQueue
from crew.core.context_store import ContextStore
from crew.master.planner import Planner

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not found in .env file")

llm_client = LLMClient(provider="gemini", model="gemma-3-1b-it", api_key=api_key)
planner = Planner(llm_client)

print("--- Planning ---")
tasks = planner.plan("build a python script that reads a CSV and prints row count")
for t in tasks:
    print(f"  {t.task_id}: {t.description}  (depends_on={t.depends_on})")

assert len(tasks) >= 2, f"Expected at least 2 tasks, got {len(tasks)}"
print(f"Planner returned {len(tasks)} tasks. OK")

print("\n--- TaskQueue ---")
queue = TaskQueue(tasks)
first = queue.pop_ready()
print(f"  First ready task: {first.task_id} — {first.description}")
assert first.depends_on == [], f"First ready task should have no dependencies, got {first.depends_on}"
print("TaskQueue pop_ready OK")

print("\n--- ContextStore ---")
context_store = ContextStore()
context_store.set("t1", "wrote parser.py")
assert context_store.get("t1") == "wrote parser.py", "ContextStore get failed"
print("ContextStore OK")

print("\nStep 2 PASSED")
