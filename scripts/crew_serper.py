import os
import sys

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

# Creating a senior researcher agent with memory and verbose mode
researcher = Agent(
  role='Senior Researcher',
  goal='Uncover groundbreaking technologies in {topic}',
  verbose=True,
  memory=True,
  backstory=(
    "Driven by curiosity, you're at the forefront of"
    "innovation, eager to explore and share knowledge that could change"
    "the world."
  ),
  tools=[search_tool],
  allow_delegation=True
)

# Creating a writer agent with custom tools and delegation capability
writer = Agent(
  role='Writer',
  goal='Narrate compelling tech stories about {topic}',
  verbose=True,
  memory=True,
  backstory=(
    "With a flair for simplifying complex topics, you craft"
    "engaging narratives that captivate and educate, bringing new"
    "discoveries to light in an accessible manner."
  ),
  tools=[search_tool],
  allow_delegation=False
)

# Research task
research_task = Task(
  description=(
    "Identify the current important research in {topic}."
    "Focus on identifying the essential scientific questions."
    "Your final report should clearly articulate the key points"
    "and ideas for novel next steps."
  ),
  expected_output='A comprehensive 3 paragraphs long report on the latest work in M6A cancer research.',
  tools=[search_tool],
  agent=researcher,
)


# Writing task with language model configuration
write_task = Task(
  description=(
    "Compose an insightful article on {topic}."
    "Focus on the latest trends and how it's impacting the industry."
    "This article should be easy to understand, engaging, and positive."
  ),
  expected_output='A 4 paragraph article on {topic} advancements formatted as markdown.',
  tools=[search_tool],
  agent=writer,
  async_execution=False,
  output_file='new-blog-post.md'  # Example of output customization
)

# Forming the tech-focused crew with some enhanced configurations
crew = Crew(
  agents=[researcher, writer],
  tasks=[research_task, write_task],
  process=Process.sequential,  # Optional: Sequential task execution is default
  memory=True,
  cache=True,
  max_rpm=100,
  share_crew=True
)

# Starting the task execution process with enhanced feedback
result = crew.kickoff(inputs={'topic': 'm6A in cancer research'})
print(result)