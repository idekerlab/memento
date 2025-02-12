# Memento

## Quick Start

### Setup
1. Clone the repository:
   ```
   git clone https://github.com/your-username/memento.git
   cd memento
   ```

2. Create a virtual environment and activate it:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

### Running the Prototype
(Instructions for running the prototype will be added as it's developed)

## Project Overview

Memento is a general-purpose agent with knowledge graph-based memory: structured episodic memory and free-form long-term memory.

The driving goal of Memento is for it to be a multi-goal, persistent, stable agent:
- It can remember what it is doing and what it has already done over arbitrary periods, not just within the current context 
- It makes plans and updates the plans as it works.
- It knows what didn't work in past actions and does not repeat failed approaches unless it has reason to believe that the situation has changed.
- It can work on multiple goals at the same time, balancing priorities of goals and actions given its resources. 
- The priority balancing means that it can set aside or abandon plans in favor of alternatives if the progress is not promising or if the goal is sufficiently satisfied for the current task 

The difference between Memento and classic knowledge representation based agents is that the reasoning and world knowledge is handled by the LLM (or LLMs), not by explicit, programmatic rules. There is no need for fully consistent knowledge representation and no need to cater to the limitations of rules. We are instead attempting to load each prompt with the relevant information, plan of action, and available tools.

Multiple actions can be proposed at a given time, linked with dependencies, forming plans. Downstream planned actions can be revised, abandoned, etc. at each step. There may be many available actions, so the agent needs to prioritize at each step. 


