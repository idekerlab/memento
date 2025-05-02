# TaskManager V2 - Redesigned Task Execution System

## Overview

TaskManagerV2 is a completely redesigned task execution system that addresses several key issues in the original implementation:

1. Eliminates complex variable resolution that was error-prone
2. Directly creates domain entities with proper types
3. Maintains clear task status tracking
4. Creates explicit relationships between tasks, results, and episodes
5. Simplifies dependency management

## Key Improvements

### 1. Simplified Data Flow

- Tasks return entity IDs directly instead of complex nested result structures
- No string interpolation for references - direct entity lookup instead
- Clean separation between task status and task output

### 2. Enhanced Error Handling

- Detailed error reporting with context preservation
- Error information stored directly on task entities
- Clear status tracking: not_executed → successful/unsuccessful

### 3. Domain-Specific Entities

- LLM tasks can specify result_type for domain modeling
- Direct creation of business objects (e.g., "Hypothesis", "GeneAnalysis")
- Relationships between domain objects are explicit

### 4. Improved Traceability

- Every created entity has relationships to its creating task and episode
- Task history is preserved in the knowledge graph
- Clear audit trail for entity provenance

## Task Types

### Entity-Creating Tasks

These tasks create domain-specific entities and return their IDs:

- `create_entity`: Explicitly creates entities with properties
- `query_database`: Creates QueryResult entities with results
- `query_llm_using_template`: Creates LLMResponse or domain-specific entities

### Operation Tasks

These tasks perform operations but don't create new entities:

- `update_entity`: Updates properties on entities
- `add_relationship`: Creates relationships between entities

## Implementation Details

### Task Status

All tasks have one of three status values:

- `not_executed`: Initial state when task is created
- `successful`: Task completed without errors
- `unsuccessful`: Task failed with error (has error_message property)

### Dependencies

Dependencies are handled by direct reference:

- Tasks specify `requires` list of output_var names
- TaskManager maintains `task_result_ids` map of output_var → entity_id
- Failed dependencies cause tasks to be skipped with "unsuccessful" status

### Template Processing

Template content is more robustly detected:

- Checks multiple property names ("template", "content")
- Handles both direct content and JSON-wrapped content
- Properly handles format strings with or without arguments

### Error Handling

Errors are clearly captured and propagated:

- Error messages stored directly on task entities
- Detailed logging with contextual information
- Consistent error formatting across all task types

## Migrating from TaskManager to TaskManagerV2

### Schema Changes

- Add `result_type` field to tasks that create entities
- Use `entity_var`, `source_var`, `target_var` for referencing previous task results
- Replace complex variable references with direct entity references

### Execution Model Changes

- Results are directly accessible by entity ID
- No need for variable substitution in task parameters
- Templates can be simplified to not require argument substitution

## Usage Example

```json
{
  "tasks": [
    {
      "type": "create_entity",
      "output_var": "template",
      "requires": [],
      "result_type": "Template",
      "entity_type": "Template",
      "name": "Gene Research Template",
      "properties": {
        "content": "Template content here..."
      }
    },
    {
      "type": "query_llm_using_template",
      "output_var": "gene_analysis",
      "requires": ["template"],
      "result_type": "GeneAnalysis",
      "template_var": "template",
      "arguments": {}
    }
  ]
}
