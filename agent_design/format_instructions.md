OUTPUT FORMAT
Your response must be a valid JSON object containing two required fields: 'reasoning' and 'tasks'.

The 'reasoning' field should document your step-by-step thought process, including:
- Assessment of the current situation
- Analysis of any relevant context
- Decision rationale
- Anticipated outcomes
- Any uncertainties or assumptions

The 'tasks' field must be an array of task objects. Valid task types are:

1. Entity Management:
{
    "type": "create_entity",
    "properties": {
        "type": "string: entity type",
        "name": "string: entity name",
        "properties": {
            "property_name": "value",
            ...
        }
    }
}

{
    "type": "update_entity",
    "entity_id": "string: entity id",
    "properties": {
        "property_name": "value",
        ...
    }
}

{
    "type": "add_relationship",
    "source_id": "string: source entity id",
    "target_id": "string: target entity id",
    "type": "string: relationship type",
    "properties": {  // optional
        "property_name": "value",
        ...
    }
}

2. Action Management:
{
    "type": "create_action",
    "properties": {
        "name": "string: concise action name",
        "description": "string: detailed action description",
        "completion_criteria": "string: how to determine if action is satisfied",
        "dependencies": ["array of entity_ids or empty array"],
        "state": "string: must be 'unsatisfied'"
    }
}

{
    "type": "update_action",
    "entity_id": "string: action entity id",
    "properties": {
        "state": "string: one of [unsatisfied, in-progress, satisfied, abandoned]",
        "state_reason": "string: explanation for state change"
    }
}

3. LLM Query:
{
    "type": "query_llm",
    "template_id": "string: prompt template entity id",
    "arguments": {
        "argument_name": "value or object",
        // For entity property reference:
        "argument_name": {
            "entity_id": "string: entity id",
            "property": "string: property name"
        }
    }
}

Example Response:
{
    "reasoning": "I need to create a hypothesis entity and link it to the relevant experimental data. I'll then create an action to analyze this data for hypothesis generation.",
    "tasks": [
        {
            "type": "create_entity",
            "properties": {
                "type": "Hypothesis",
                "name": "Initial_Hypothesis_20250120",
                "properties": {
                    "status": "draft",
                    "created_date": "2025-01-20"
                }
            }
        },
        {
            "type": "add_relationship",
            "source_id": "456",  // hypothesis entity
            "target_id": "789",  // experiment data entity
            "type": "references_data"
        },
        {
            "type": "create_action",
            "properties": {
                "name": "Analyze experiment data for hypothesis generation",
                "description": "Review experimental results to formulate initial hypothesis",
                "completion_criteria": "Hypothesis entity updated with initial proposal",
                "dependencies": [],
                "state": "unsatisfied"
            }
        }
    ]
}

4. Database Query:
{
    "type": "query_database",
    "sql": "string: SELECT query for knowledge graph database",
    "description": "string: purpose of this query"  // helps track reasoning
}

Note: Database queries must be read-only SELECT statements against the knowledge graph tables:
- entities (id, type, name)
- properties (entity_id, key, value)
- relationships (id, source_id, target_id, type)

Example Response:
{
    "reasoning": "I need to find all active hypothesis-related actions and their dependencies before creating new analysis tasks.",
    "tasks": [
        {
            "type": "query_database",
            "sql": """
                SELECT e.id, e.name, p.value as state
                FROM entities e
                JOIN properties p ON e.id = p.entity_id
                WHERE e.type = 'Action'
                AND EXISTS (
                    SELECT 1 FROM properties 
                    WHERE entity_id = e.id 
                    AND key = 'state'
                    AND value = 'unsatisfied'
                )
                AND e.name LIKE '%hypothesis%'
            """,
            "description": "Find unsatisfied hypothesis-related actions"
        },
        {
            "type": "query_llm",
            "template_id": "template_123",
            "arguments": {
                "current_actions": "{{last_query_results}}"
            }
        }
    ]
}