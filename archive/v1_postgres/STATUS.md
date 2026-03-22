# Memento Project Status

## Recent Updates (March 5, 2025)

### Completed Tasks

1. **Refactored Schema and Instructions Storage**
   - Moved `EPISODE_TOOL_SCHEMA` from hardcoded constant to `schema.json` file
   - QueryManager now loads the schema from file at initialization
   - Primary instructions are loaded from `primary_instructions.txt`
   - This eliminates issues with string escaping (especially triple quotes)

2. **Fixed Anthropic Tool Protocol Integration**
   - Updated LLM class to handle API format differences 
   - Added automatic conversion from OpenAI-style tool format to Anthropic tool format
   - Fixed tool_choice format from `{"type": "function", "function": {"name": "..."}}` to `{"type": "tool", "tool": {"name": "..."}}`
   - All tool protocol tests now pass with both mocked and live API calls

3. **Improved JSON Repair Functionality**
   - Enhanced regex patterns for unquoted property names detection
   - Added better handling of single-quoted strings and triple quotes
   - Improved the manual JSON building with more robust extraction
   - Fixed JSON parsing issues with malformed responses

4. **Added Comprehensive Testing**
   - Created test suite for JSON repair functionality
   - Added tests for tool protocol with mocked API
   - Implemented live API tests to verify real-world behavior
   - All tests now pass successfully

### Current Issues Being Addressed

1. **run_from_snapshot.py Errors**
   - Initial error was due to incorrect tool_choice format
   - Fixed with format conversion in LLM class
   - Need to verify with actual run_from_snapshot.py execution

### Next Steps

1. **Integration Testing**
   - Verify that all components work together correctly
   - Test with real episode creation and execution
   - Monitor for any additional issues

2. **Code Review and Documentation**
   - Review all changes for potential edge cases
   - Update documentation to reflect the new architecture
   - Add comments for any complex logic

3. **Performance Optimization**
   - Identify any bottlenecks in the LLM query process
   - Consider caching strategies for repeated queries
   - Optimize JSON parsing and repair for large responses

## Repository Structure

Key files modified:
- `query_manager.py` - Updated to load schema and instructions from files
- `llm.py` - Improved JSON repair and tool protocol handling
- `schema.json` - New file containing the EPISODE_TOOL_SCHEMA
- `primary_instructions.txt` - Existing file with instructions (unchanged)
- `tests/` - New and updated test files
