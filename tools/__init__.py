from crew.tools.write_file import write_file
from crew.tools.read_file import read_file
from crew.tools.run_code import run_code
from crew.tools.list_dir import list_dir
from crew.tools.ask_master import ask_master

TOOLS = {
    "write_file": write_file,
    "read_file": read_file,
    "run_code": run_code,
    "list_dir": list_dir,
    "ask_master": ask_master,
}
