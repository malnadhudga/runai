from runai.tools.write_file import write_file
from runai.tools.read_file import read_file
from runai.tools.run_code import run_code
from runai.tools.list_dir import list_dir
from runai.tools.ask_master import ask_master

TOOLS = {
    "write_file": write_file,
    "read_file": read_file,
    "run_code": run_code,
    "list_dir": list_dir,
    "ask_master": ask_master,
}
