import os

from crew.core.task import Task
from crew.core.task_queue import TaskQueue
from crew.core.context_store import ContextStore
from crew.tools.write_file import write_file
from crew.tools.read_file import read_file
from crew.tools.run_code import run_code
from crew.tools.list_dir import list_dir
from crew.slave.scratchpad import Scratchpad

# ── Task + TaskQueue ──────────────────────────────────

t1 = Task(task_id="t1", description="write parser.py", depends_on=[])
t2 = Task(task_id="t2", description="write fetcher.py", depends_on=[])
t3 = Task(task_id="t3", description="write main.py", depends_on=["t1", "t2"])

queue = TaskQueue([t1, t2, t3])

first = queue.pop_ready()
assert first is not None
assert first.task_id in ("t1", "t2"), f"Expected t1 or t2 first, got {first.task_id}"
print(f"  pop_ready #1: {first.task_id} (OK — no deps)")

second = queue.pop_ready()
assert second is not None
assert second.task_id in ("t1", "t2"), f"Expected t1 or t2, got {second.task_id}"
assert second.task_id != first.task_id
print(f"  pop_ready #2: {second.task_id} (OK — no deps)")

blocked = queue.pop_ready()
assert blocked is None, "t3 should be blocked"
print("  pop_ready #3: None (OK — t3 blocked on t1,t2)")

queue.mark_done(first.task_id, "done", [])
queue.mark_done(second.task_id, "done", [])

third = queue.pop_ready()
assert third is not None
assert third.task_id == "t3"
print(f"  pop_ready #4: {third.task_id} (OK — deps satisfied)")

queue.mark_done("t3", "done", [])
assert queue.is_complete(), "Queue should be complete"
print("  is_complete: True (OK)")
print("Task + TaskQueue: PASSED\n")

# ── ContextStore ──────────────────────────────────────

ctx = ContextStore()
ctx.set("t1", "wrote parser.py")
ctx.set("t2", "wrote fetcher.py")
assert ctx.get("t1") == "wrote parser.py"
assert ctx.get("t2") == "wrote fetcher.py"
assert "t1" in ctx.summary()
assert os.path.isfile(os.path.join("workspace", "context.json"))
print("ContextStore: PASSED\n")

# ── Tools ─────────────────────────────────────────────

result = write_file("hello.py", "print('hello')")
assert "ok" in result, f"write_file failed: {result}"
print(f"  write_file: {result}")

result = read_file("hello.py")
assert "print('hello')" in result, f"read_file failed: {result}"
print(f"  read_file: got {len(result)} chars")

result = run_code("hello.py")
assert "hello" in result, f"run_code failed: {result}"
print(f"  run_code: {result.strip()}")

result = list_dir()
assert "hello.py" in result, f"list_dir failed: {result}"
print(f"  list_dir: {result}")

print("Tools: PASSED\n")

# ── Scratchpad ────────────────────────────────────────

pad = Scratchpad("slave-1", task=None)
pad.append_user("do something")
pad.append_assistant("I will write code")
pad.append_tool_result("write_file", "ok: wrote 42 bytes to test.py")
assert len(pad.messages) == 3
assert pad.is_maxed_out() is False
print(f"  messages: {len(pad.messages)}, maxed_out: False (OK)")

for _ in range(15):
    pad.increment()
assert pad.is_maxed_out() is True
print(f"  after 15 increments: maxed_out: True (OK)")

msgs = pad.get_messages()
assert all(m["role"] != "system" for m in msgs)
print("Scratchpad: PASSED\n")

print("Step 2 PASSED — no API calls needed")
