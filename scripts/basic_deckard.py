import os
import sys

# Get the current working directory. We should be running the script in the memento repo directory
cwd = os.getcwd()
# print("\nCurrent working directory:", cwd)

# Get the parent directory of the current working directory which should be the one with all the repos
all_repos = os.path.dirname(cwd)
# print("\nall repos directory:", all_repos)

# make the path to the agent_evaluation repo
ae_repo = os.path.join(all_repos, "agent_evaluation")
print(f'\nagent_evaluation path: {ae_repo}\n')

# insert the path into sys.path
sys.path.insert(0, ae_repo)

# ae_app = os.path.join(all_repos, ae_repo)
#sys.path.insert(0, ae_app)

for path in sys.path:
    print(path)

from memento.config import load_api_keys, load_database_uri
from memento.sqlite_database import SqliteDatabase
from models.llm import LLM
from models.agent import Agent
print('\n\ndone with imports\n')

database_uri = load_database_uri()
print(f'\ndatabase_uri = {database_uri}')
api_keys = load_api_keys()
print(f'\napi_keys = {api_keys}')

db = SqliteDatabase(database_uri)

llm = LLM.create(db, 
                 type="Groq", 
                 model_name='llama-3.1-8b-instant',
                 seed=42,
                 temperature=1.0)

commedian = Agent.create(db, llm.object_id, 
                         "you are a brilliant writer of narative, skit-based humor. In an alternate universe, you were the equivalent of the Pythons, Spike Jones, Douglas Adams, and Noel Fielding all rolled into one.", 
                         "write me an absurdist, 'pythonesque' script with ten lines about {topic}")

result = commedian.run(properties={'topic': "Unusual food truck in San Diego."})

print(result)



