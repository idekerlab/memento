import os
import sys
os.environ["SERPER_API_KEY"] = "08b8d890a30174ab3ed8d6be341054836e87d91c"  # serper.dev API key

cwd = os.getcwd() # Current working directory
dirname = os.path.dirname(cwd) # Parent directory
print(cwd)
print(dirname)
sys.path.append(dirname)# Add the parent directory to the Python path
print(sys.path)

from crewai import Agent
from crewai_tools import SerperDevTool
search_tool = SerperDevTool()
#from langchain_community.retrievers import PubMedRetriever
#search_tool = PubMedRetriever()
from crewai import Task
from crewai import Crew, Process

# MARK: - Agents
# Creating a senior researcher agent with memory and verbose mode
researcher = Agent(
  role='Senior Researcher',
  goal='Review and analyze recent scientific progress in {topic}',
  verbose=True,
  memory=True,
  backstory=(
    "You are a senior scientist who is keenly analytical and well-versed in your field."
    "You start every thought with '(Senior Researcher)'"
  ),
  tools=[search_tool],
  allow_delegation=True
)

# Creating a writer agent with custom tools but no delegation capability
writer = Agent(
  role='Writer',
  goal='Narrate compelling brief reviews of about {topic} for the general scientific audience.',
  verbose=True,
  memory=True,
  backstory=(
    "With a flair for simplifying complex topics, you craft"
    "engaging narratives that communicate the latest"
    "discoveries to light in an accessible manner."
    "You start every thought with '(Writer)'"
  ),
  tools=[search_tool],
  allow_delegation=False
)

# MARK: - Tasks
# Research task
research_task = Task(
  description=(
    "Identify the current important recent research in {topic}."
    "Focus on identifying the essential scientific questions and findings."
    "Your final report should also speculate on posible future directions in the field."
  ),
  expected_output='A comprehensive 3 paragraphs long report on the latest work in m6A cancer research.',
  tools=[search_tool],
  agent=researcher,
)

# Writing task with language model configuration
write_task = Task(
  description=(
    "Compose an insightful article on the latest findings in {topic}."
    "This article should be directed at the scientists in {broader_topic}, rather than experts in {topic}."
  ),
  expected_output='A 4 paragraph article on {topic} advancements formatted as HTML.',
  tools=[search_tool],
  agent=writer,
  async_execution=False,
  output_file='new-blog-post.md'  # Example of output customization
)

# MARK: - Crew
# Forming the science-focused crew with some enhanced configurations
crew = Crew(
  agents=[researcher, writer],
  tasks=[research_task, write_task],
  process=Process.sequential,  # Optional: Sequential task execution is default
  memory=True,
  cache=True,
  max_rpm=100,
  share_crew=True
)

# MARK: - Execution
# Starting the task execution process with enhanced feedback
result = crew.kickoff(inputs={'topic': 'm6A', 'broader_topic': 'cancer research'})
print(result)