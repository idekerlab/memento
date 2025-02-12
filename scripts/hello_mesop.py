import mesop as me
import sys
import os

cwd = os.getcwd() # Current working directory
dirname = os.path.dirname(cwd) # Parent directory
print(cwd)
print(dirname)
sys.path.append(dirname)# Add the parent directory to the Python path
print(sys.path)

#print("Hello World" + me.__version__)

from datetime import datetime
import numpy as np
import pandas as pd
import mesop as me
import time
from memento.llm import LLM

llm = LLM(type="Groq", model_name="llama3-70b-8192", max_tokens=300, seed=42, temperature=0.5) 

discussion: list = []
dataset: str = ""
hypothesis: str = ""
critique_template: str = """
You are {you}, a scientist discussing a hypothesis and experiment plan with {them}, 
your friend and long-time collaborator 
The hypothesis was proposed by Jane, a graduate student as mechanism that explains
some of the experimental data in the dataset provided below.
Your goal is to critique the hypothesis and the experiment that has been proposed,
ultimately deciding whether it is worth pursuing further, especially in light of
the limited resources available, its plausibility, and its novelty.

Important: Reply briefly and succinctly, making only one point, to the last statement in the provided conversation.
If there is no previous statement, present your initial analysis of the hypothesis. 

Use a casual tone, but be sharply analytical and do not
hold back when you find flaws in the hypothesis or your colleagues statements. 

Do not thank {them} constantly.
Briefly acknowledge when you agree with them before making your next point.
For example: "Yes, good point." or "I see what you mean, but I think..." or "OK, good. But what about...".

When you find that you and your colleague are largely in agreement,
summarize the key points of the evaluation and propose that the dialog can conclude.
If your colleague make such a proposal to you, consider the situation and 
either reply 'Yes' or say 'No' and explain your remaining concerns.

<experiment>
{experiment}
</experiment>

<dataset>
{dataset}
</dataset>

<hypothesis>
{hypothesis}
</hypothesis>

<discussion>
{discussion}
</discussion>
"""

scientist_1_name = "Susan"
scientist_2_name = "Hiroshi"

def discussion_to_string(discussion):
  return "\n\n".join([f"{v}" for v in discussion])

def compose_prompt(template, speaker, listener, dataset, experiment, hypothesis, discussion):
  return template.format(dataset=dataset, 
                         hypothesis=hypothesis, 
                         experiment=experiment,
                         discussion=discussion_to_string(discussion),
                         you=speaker,
                         them=listener)

with open("../data/dengue_with_uniprot_top_49.csv", 'r') as file:
        dataset = file.read()

with open("../data/test_hypothesis.txt", 'r') as file:
        hypothesis = file.read()

def discussion_turn():
  global discussion
  global dataset
  global hypothesis
  global critique_template
  global scientist_1_name
  global scientist_2_name
  state = me.state(State)
  prompt = compose_prompt(critique_template, state.speaker, state.listener, 
                            dataset, "", hypothesis, discussion)
  response = llm.query("", prompt)
  discussion.append(f'## {state.speaker}:\n\n - {response}')
  print(f'{state.speaker}: \nresponded: {response}')
  state.speaker, state.listener = state.listener, state.speaker
  state.discussion_string = discussion_to_string(discussion)


@me.stateclass
class State:
  start_stop_label: str = "Start"
  running: bool = False
  speaker: str = "Susan"
  listener: str = "Hiroshi"
  discussion_string: str = "## Starting the discussion\n\n"

@me.page()
def app():
  state = me.state(State)

  with me.box(style=me.Style(padding=me.Padding.all(10), width=500)):
      me.button("Next", type="flat", on_click=on_click_discussion_turn)
      #me.text(f'Running: {state.running}')

  with me.box(style=me.Style(width=800, 
                             height=800, 
                             overflow_y='scroll',
                             padding=me.Padding.all(10),
                             border_radius=5,
                             border=me.Border.symmetric(horizontal=me.BorderSide(width=2, color="pink", style="solid"),
                                                        vertical=me.BorderSide(width=2, color="orange", style="solid")
                             ))):
    me.markdown(state.discussion_string)
  
 
def on_click_discussion_turn(e):
  discussion_turn()

