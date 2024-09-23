import os
import sys

# Get the current working directory. We should be running the script in the memento repo directory
cwd = os.getcwd()
print("\nCurrent working directory:", cwd)

# Get the parent directory of the current working directory which should be the one with all the repos
all_repos = os.path.dirname(cwd)
print("\nall repos directory:", all_repos)

# # Get the grandparent directory (which should be the project root)
# project_root = os.path.dirname(parent_dir)
# print("\nProject root directory:", project_root)

# # Get the directory containing all the repos
# all_repos = os.path.dirname(project_root)
# print(f'\nAll repo directory: {all_repos}')

# Add the path to the CXDB repo
cxdb_repo = os.path.join(all_repos, "cxdb")
print(f'\ncxdb path: {cxdb_repo}\n')

# Add the cwd ( memento project root) to the Python path
sys.path.insert(0, cwd)

# Add the cxdb_rep path to the Python path
sys.path.insert(0, cxdb_repo)

print("\nUpdated sys.path:", sys.path)

# Now try to import the CXDB class
from cxdb.core import CXDB

# Rest of your script
my_db = CXDB()
my_db.add_node("Node1", "Type1", {"prop1": "value1"})
print(my_db.nodes)