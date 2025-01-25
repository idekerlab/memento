# Memento Agent Design State: January 24, 2025

### Memory Architecture
- Episodic: Chain of episodes connected by previous_episode relationships, linked to Tasks and Task Results performed in the Episode
- Actions: Goals and plans stored as Action entities with states and dependencies.  
- Procedural: prompt templates, SQL templates, and other procedural information that can be used with Tasks
- Factual: knowledge stored by the agent

## Core Entity Types
- Episodes: Track operations and context

- Task: Work units specified in the Episode query response, created as entities linked to the Episode and the Action that the Task serves

- Result: Task outputs linked to the task.
  * example_query_llm_result  (query_llm_result has unparsed content. The agent can decide what to do with it, such as making an entity corresponding to the result, in a subsequent episode)
- Action: Goals and sub-goals
- Dataset:
  * 
- PromptTemplate: 

### Episode
- example_llm_episode
#### Properties
#### Relationships
- previous_episode

### Task
- example_query_llm_task
- supports both value and reference arguments
- no ordering of tasks within an episode, tasks within an episode have no interdependencies
#### Types
1. create_action: Create new Actions with properties and dependencies
2. update_action: Modify Action state and properties
3. query_llm: Use prompt templates to get LLM assistance
#### Properties
#### Relationships
- task_of (links to the Episode)

### Result
#### Properties
#### Relationships
- result_of (links to Task)

### Dataset
- example_kynurenine_dataset
#### Properties
- name
- experiment_description
- biological_context
- data
#### Relationships

### PromptTemplate
- templates to use in query_llm tasks
- example_hypothesis_template
#### Properties
- name
- version
- template
- context 
#### Relationships

### Action 
#### Properties
- active
  - TRUE means that it is included in the episode prompt
- state:
  - unsatisfied: Action needs to be worked on
  - in-progress: Currently being processed
  - satisfied: Successfully completed
  - abandoned: Determined to be unachievable via current approach
- description: can hold arbitrary documentation, notes, outcomes that the Agent thinks will be useful to remember
- completion_criteria
#### Relationships
- "depends_on"
- Agent prioritizes Actions with no depends_on unsatisfied Actions

## Episode Workflow 
1. Assessment: Review actionable items and relevant context
2. Planning: Break down complex actions when needed
3. Execution: In the response, specify Tasks to progress one or more Actions
4. Evaluation: Assess results and update Action states



### 4. Key Relationships
- Episodes: previous_episode relationships form linear chain
- Tasks: belong to Episodes (task_of)
- Results: linked to Tasks (result_of)
- Hypotheses: derived_from Result, used_prompt Template, used_dataset Dataset

### 5. Multi-Episode Workflows
- Separate episodes for LLM queries and entity creation
- Clear linkage between related episodes
- Support for review and reflection tasks

## Development Status

### 1. Test Implementation Focus
- Primary test: test_create_hypothesis.py to verify multi-step hypothesis generation
- Starting with example entities:
  * example_kynurenine_dataset (Dataset)
  *  (PromptTemplate)
  * example_llm_episode (Episode)
  * example_query_llm_task (Task)
  * example_query_llm_result (Result)
- Test validates:
  * Action decomposition
  * Episode chaining
  * Sub-action completion
  * Plan execution through tasks

### 2. Test Goals
- Sub-actions created during initial planning
- currently active Actions included in the episode prompt (describing the current plan)
- LLM queries perform template validation
- Tasks must return standardized error reporting
- Actions, Episodes, and Tasks are correctly updated

## Outstanding Questions

### 1. Task Management
- Schema for defining task argument types (value vs reference)
- Output parsing configuration and validation
- How to specify expected result types

### 3. Result Processing
- Standard format for task results
- How to handle partial or failed results
- Result validation rules
