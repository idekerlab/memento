# Refactoring Notes: Schema and Instructions Externalization

## Problem

The `query_manager.py` file contained large embedded string constants for both:
1. Primary instructions for the LLM
2. Schema definition for the Episode Tool

This created several issues:
- String escaping problems (especially with triple quotes)
- Poor maintainability of long text blocks in code
- Difficulty in version controlling and reviewing changes to these text components

## Solution

We extracted these text components to separate files:

1. `primary_instructions.txt` - Already existed and contained the primary instructions
2. `schema.json` - New file containing the Episode Tool schema

The `QueryManager` class was updated to load these files during initialization.

## Implementation Details

1. The `PRIMARY_INSTRUCTIONS` constant was replaced with a file read operation.
2. The `EPISODE_TOOL_SCHEMA` constant was moved to `schema.json`.
3. Both files are loaded in the `QueryManager.__init__` method.

## Benefits

- No more string escaping issues with triple quotes
- Cleaner code with external resources loaded at runtime
- Better separation of concerns between code and content
- Easier to maintain and update the instructions and schema
- Improved version control for text content

## Testing

Created a validation script (`validate_refactor.py`) to verify:
- Files exist and are accessible
- Files contain valid content
- `QueryManager` can load them correctly

## Future Improvements

- Add proper error handling if files are missing
- Consider using a configuration system for file paths
- Add versioning to schema files
