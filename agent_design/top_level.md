Here's a cleaned up summary of the Memento agent design discussion:

# Memento Agent Design: Goal-Oriented Planning and Execution

## Overview
Memento agents are autonomous systems that maintain memory of episodic, procedural, mission, and factual content across sessions. They store state, knowledge, and operational methods in a knowledge graph, allowing careful control of context for self-queries while staying within target token ranges.

## Core Concepts

### Goals and Actions
- Goals are implemented as high-level Actions, focusing on describing desired results
- Complex goals are broken down into more granular Actions with dependencies
- Actions have explicit completion criteria and state tracking
- Failed approaches are preserved as valuable context

### Action States
- unsatisfied: Action needs to be worked on
- in-progress: Currently being processed
- satisfied: Successfully completed
- abandoned: Determined to be unachievable via current approach

### Dependencies
- Initial implementation uses simple "depends_on" relationships
- Future consideration for distinguishing between "requires" vs "would satisfy"
- Agent prioritizes Actions with no unsatisfied dependencies

### Agent Workflow
1. Assessment: Review actionable items and relevant context
2. Planning: Break down complex actions when needed
3. Execution: Create and run tasks to progress selected Action
4. Evaluation: Assess results and update Action states

### Task Types
1. create_action: Create new Actions with properties and dependencies
2. update_action: Modify Action state and properties
3. query_llm: Use prompt templates to get LLM assistance

### Memory Management
- Episodic Memory: Captures reasoning and operations per episode
- Action Memory: Tracks goals and plans
- Knowledge Memory: Stores domain knowledge and templates

### Prompt Templates
- Text templates with slot notation for entity properties
- Initial implementation uses flat property access {entity.property}
- Templates can reference entities or literal values

## Implementation Notes
- Knowledge graph should separate generic, mission-specific, and instance-specific entities
- Agent core software should remain task and mission agnostic
- Knowledge graphs can be saved to capture agent types, versions, or state snapshots
- Agent flexibly decides when to enter planning mode without hardcoded triggers

This design supports scale flexibility (immediate vs long-term planning), failure recovery (abandonment + new approaches), and effective context management (episode vs action storage).