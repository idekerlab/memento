import os
import sys

# Get the current working directory
cwd = os.getcwd()
print("\nCurrent working directory:", cwd)

# Get the parent directory of the current working directory
parent_dir = os.path.dirname(cwd)
print("\nParent directory:", parent_dir)

# Get the grandparent directory (which should be the project root)
project_root = os.path.dirname(parent_dir)
print("\nProject root directory:", project_root)

# Add the project root to the Python path
sys.path.insert(0, cwd)
print("\nUpdated sys.path:", sys.path)

# Now try to import the CXDB class
from app.cxdb import CXDB

# Rest of your script
my_db = CXDB()
my_db.add_node("Node1", "Type1", {"prop1": "value1"})
print(my_db.nodes)