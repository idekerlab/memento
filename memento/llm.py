import anthropic
from memento.config import load_api_key
import json
import re
import unicodedata

class LLM:
    def __init__(self, type=None, model_name="claude-3-5-sonnet-20241022",
                 max_tokens=8096, seed=42, temperature=0.7,
                 object_id=None, created=None, name=None, description=None):
        self.type = type
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.seed = seed
        self.temperature = temperature
        self.object_id = object_id
        self.created = created
        self.name = name
        self.description = description

    async def query(self, context, prompt, tools=None, tool_choice=None):
        """Main query method that routes to appropriate model"""
        self.max_tokens = int(self.max_tokens)
        self.temperature = float(self.temperature)
        self.seed = int(self.seed)

        # For now just handle Anthropic since that's what we're testing
        if self.type == 'Anthropic':
            try:
                return self.query_anthropic(context, prompt, tools=tools, tool_choice=tool_choice)  # Don't await here
            except Exception as e:
                raise Exception(f"Query failed: {str(e)}")
        else:
            raise ValueError(f"Unsupported llm type: {self.type}")

    def query_anthropic(self, context, prompt, tools=None, tool_choice=None):
        """Synchronous wrapper around Anthropic API call"""
        key = load_api_key("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
            
        client = anthropic.Anthropic(api_key=key)
        
        try:
            messages = [{"role": "user", "content": f"{context}\n\n{prompt}"}]
            
            kwargs = {
                "model": self.model_name,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": messages
            }
            
            # Convert OpenAI-style tools to Anthropic format
            if tools:
                anthropic_tools = []
                for tool in tools:
                    if isinstance(tool, dict) and "type" in tool and tool["type"] == "function":
                        if "function" in tool:
                            # Extract function data directly
                            function_data = tool["function"]
                            
                            # Create Anthropic tool format - directly copying fields
                            anthropic_tool = {
                                "name": function_data.get("name", ""),
                                "description": function_data.get("description", ""),
                                "input_schema": function_data.get("parameters", {})
                            }
                            anthropic_tools.append(anthropic_tool)
                        else:
                            print(f"Skipping tool due to missing 'function' field: {tool}")
                    else:
                        # Skip tools that don't match expected format
                        print(f"Skipping tool with unsupported type: {tool}")
                
                kwargs["tools"] = anthropic_tools
                print(f"Original tools: {tools}")
                print(f"Converted tools for Anthropic: {anthropic_tools}")
            
            # Format tool_choice correctly for Anthropic
            if tool_choice:
                if isinstance(tool_choice, dict):
                    if "type" in tool_choice and tool_choice["type"] == "function":
                        # Convert from OpenAI format to Anthropic format
                        if "function" in tool_choice and "name" in tool_choice["function"]:
                            # Get the tool name for Anthropic format
                            tool_name = tool_choice["function"]["name"]
                            
                            # Use the proper Anthropic format
                            kwargs["tool_choice"] = {"type": "tool", "name": tool_name}
                            print(f"Original tool_choice: {tool_choice}")
                            print(f"Converted tool_choice for Anthropic: {kwargs['tool_choice']}")
                        else:
                            # Use auto if we can't extract a name
                            kwargs["tool_choice"] = {"type": "auto"}
                            print(f"Cannot extract tool name, defaulting to 'auto'")
                    else:
                        # If it already has 'type' but not 'function', pass through
                        kwargs["tool_choice"] = tool_choice
                        print(f"Using tool_choice as provided: {tool_choice}")
                else:
                    # If not a dict, convert to auto
                    kwargs["tool_choice"] = {"type": "auto"}
                    print(f"Non-dict tool_choice, defaulting to 'auto'")
            elif tools and len(tools) == 1:
                # If there's only one tool and no explicit choice, use it
                if anthropic_tools and len(anthropic_tools) == 1:
                    kwargs["tool_choice"] = {"type": "tool", "name": anthropic_tools[0]["name"]}
                    print(f"Single tool available, setting tool_choice to: {kwargs['tool_choice']}")
            
            # Debug info before API call
            print(f"=== ANTHROPIC API CALL DEBUG ===")
            print(f"Model: {self.model_name}")
            print(f"Max tokens: {self.max_tokens}")
            print(f"Temperature: {self.temperature}")
            print(f"Message content length: {len(messages[0]['content'])}")
            if "tools" in kwargs:
                print(f"Tools count: {len(kwargs['tools'])}")
                for i, tool in enumerate(kwargs['tools']):
                    print(f"Tool {i+1} name: {tool.get('name')}")
                    print(f"Tool {i+1} full content: {json.dumps(tool)}")
            if "tool_choice" in kwargs:
                print(f"Tool choice: {kwargs['tool_choice']}")
            print(f"================================")
            
            # Make the API call
            response = client.messages.create(**kwargs)
            return response
                
        except Exception as e:
            error_detail = str(e)
            print(f"Anthropic API call failed with error: {error_detail}")
            raise Exception(f"Anthropic API call failed: {error_detail}")

    async def query_and_parse_json(self, context, prompt, tools=None, tool_choice=None):
        """
        Queries the LLM and attempts to parse the response as JSON with error recovery.
        
        Returns:
            tuple: (parsed_json, repair_info)
                - parsed_json: The successfully parsed JSON object
                - repair_info: String describing errors encountered and fixed (None if no errors)
        
        Raises:
            JSONDecodeError: If JSON parsing fails even after repair attempts
            Exception: For other errors during the query or parsing process
        """
        try:
            # Make the API call
            response = await self.query(context, prompt, tools, tool_choice)
            
            # Check if this is a tool use response by examining response structure
            has_tool_use = False
            
            # Print response structure to debug
            if hasattr(response, 'content') and len(response.content) > 0:
                content_type = type(response.content[0]).__name__
                print(f"Response content[0] type: {content_type}")
                
                # Detect ToolUseBlock directly
                if content_type == 'ToolUseBlock':
                    has_tool_use = True
                    # Extract tool name and input
                    tool_name = response.content[0].name
                    tool_input = response.content[0].input
                    print(f"Received tool use response from {tool_name}")
                    print(f"Tool input: {tool_input}")
                    return tool_input, f"Tool response from {tool_name}"
                
                # Try to access tool_use attribute if available
                elif hasattr(response.content[0], 'tool_use') and response.content[0].tool_use:
                    tool_use = response.content[0].tool_use
                    has_tool_use = True
                    print(f"Received tool use response from {tool_use.name} with input: {tool_use.input}")
                    return tool_use.input, "Tool response (no JSON parsing needed)"
            
            # If there's no tool use, try to extract text content
            if not has_tool_use:
                # For TextBlock type content
                if hasattr(response, 'content') and hasattr(response.content[0], 'text'):
                    response_text = response.content[0].text
                    if not response_text:
                        raise ValueError("No text content found in response")
                
                # For direct content (less likely but possible)
                elif hasattr(response, 'text'):
                    response_text = response.text
                
                # If we can't find text, dump the entire response structure for debugging
                else:
                    print(f"Response content type: {type(response.content[0]).__name__}")
                    print(f"Available attributes: {dir(response.content[0])}")
                    raise ValueError("Could not find text content in response - unsupported response format")
                
                # Print a preview of the response
                print(f"Response text preview (first 200 chars): {response_text[:200]}...")
                
                # First attempt to parse as-is
                try:
                    parsed_json = json.loads(response_text)
                    return parsed_json, None  # No repair needed
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {str(e)} at position {e.pos}")
                    print(f"Context: '{response_text[max(0, e.pos-20):min(len(response_text), e.pos+20)]}'")
                    
                    # Try to repair the JSON
                    repair_info = []
                    fixed_json_text = self._repair_json(response_text, repair_info)
                    
                    # Try to parse the repaired JSON
                    try:
                        parsed_json = json.loads(fixed_json_text)
                        return parsed_json, "\n".join(repair_info)
                        
                    except json.JSONDecodeError as secondary_e:
                        # If we still can't parse, try direct simple replacement of triple quotes
                        repair_info.append("Attempting simple triple quote fix...")
                        
                        # Replace triple quotes directly with single quotes
                        simple_fixed = response_text.replace('"""', '"')
                        
                        try:
                            parsed_json = json.loads(simple_fixed)
                            repair_info.append("Simple triple quote replacement worked")
                            return parsed_json, "\n".join(repair_info)
                        except json.JSONDecodeError:
                            # If still fails, try the manual approach
                            repair_info.append("Attempting manual JSON building...")
                            manual_json = self._build_json_manually(response_text, repair_info)
                            
                            try:
                                parsed_json = json.loads(manual_json)
                                return parsed_json, "\n".join(repair_info)
                            except json.JSONDecodeError:
                                # If all repairs fail, raise the original error with repair context
                                error_msg = f"JSON repair failed. Original error: {str(e)}."
                                raise json.JSONDecodeError(
                                    error_msg, 
                                    doc=response_text, 
                                    pos=e.pos
                                )
                
        except Exception as e:
            if isinstance(e, json.JSONDecodeError):
                raise  # Re-raise JSON errors as they've already been handled
            raise Exception(f"Error querying LLM or parsing response: {str(e)}")

    def _repair_json(self, text, repair_info):
        """
        Attempts to repair common JSON formatting issues.
        
        Args:
            text: The JSON string to repair
            repair_info: List to append repair information to
            
        Returns:
            str: The repaired JSON string
        """
        original_text = text
        
        # Fix 0: Trim whitespace from beginning and end
        text = text.strip()
        if text != original_text:
            repair_info.append("Trimmed whitespace from beginning and end")
        
        # Fix 1: Replace triple quotes with regular quotes - more aggressive approach
        # Look for """ and replace with " - important to handle both opening and closing cases
        text = text.replace('"""', '"')
        if '"""' in original_text:
            repair_info.append("Replaced all triple quotes with single quotes")
        
        # Fix 2: Handle missing quotes around property names - improved regex
        # This regex matches property names that aren't in quotes but followed by a colon
        # The previous pattern was too restrictive and likely missed some cases
        unquoted_key_pattern = r'([{,]\s*)(\w+)(\s*):(\s*)'
        text = re.sub(unquoted_key_pattern, r'\1"\2"\3:\4', text)
        
        # Also handle start of JSON object case (no preceding {,)
        text = re.sub(r'^\s*(\w+)(\s*):(\s*)', r'"\1"\2:\3', text)
        
        repair_info.append("Fixed unquoted property names")
        
        # Fix 3: Handle single quotes used as string delimiters
        # This regex finds string values delimited by single quotes and converts them to double quotes
        single_quoted_strings = r"(?<![\\])(')((?:\\.|[^\\'])*?)(?<![\\])(')(?=\s*[,}]|\s*$)"
        text = re.sub(single_quoted_strings, r'"\2"', text)
        repair_info.append("Converted single-quoted strings to double-quoted strings")
        
        # Fix 4: Handle single quotes within already quoted strings
        if "'" in text:
            # Replace single quotes with escaped single quotes within string literals
            in_string = False
            result = []
            
            i = 0
            while i < len(text):
                char = text[i]
                
                if char == '"' and (i == 0 or text[i-1] != '\\'):
                    # Toggle string mode when we encounter an unescaped quote
                    in_string = not in_string
                    result.append(char)
                elif char == "'" and in_string:
                    # If we're inside a string and find a single quote, escape it
                    result.append("\\'")
                    repair_info.append("Escaped single quotes within strings")
                else:
                    result.append(char)
                    
                i += 1
                
            text = ''.join(result)
        
        # Fix 5: Handle trailing commas in arrays/objects
        text = re.sub(r',(\s*[\]}])', r'\1', text)
        if ',' in original_text and re.search(r',\s*[\]}]', original_text):
            repair_info.append("Removed trailing commas")
        
        # Fix 6: Handle newlines in string literals more carefully
        # We'll keep them intact but ensure they're properly escaped
        result = []
        in_string = False
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                # Toggle string mode for unescaped quote
                in_string = not in_string
                result.append(char)
            elif char == '\n' and in_string:
                # Replace literal newlines in strings with \\n
                result.append('\\n')
                repair_info.append("Replaced literal newline in string with \\n")
            else:
                result.append(char)
                
            i += 1
            
        text = ''.join(result)
        
        # Fix 7: Remove control characters
        control_chars = [chr(i) for i in range(32) if i != 10 and i != 13 and i != 9]  # exclude newline, CR, tab
        for char in control_chars:
            if char in text:
                text = text.replace(char, '')
                repair_info.append(f"Removed control character: '\\x{ord(char):02x}'")
                
        # Fix 8: Normalize Unicode (handle special quotation marks, etc.)
        normalized = unicodedata.normalize('NFKC', text)
        if normalized != text:
            text = normalized
            repair_info.append("Normalized Unicode characters")
            
        # Return repaired text
        if original_text == text:
            repair_info.append("No repairs made")
        
        return text
    
    def _build_json_manually(self, text, repair_info):
        """
        A method that attempts to manually extract and rebuild the JSON structure
        from the text by identifying key components.
        
        Args:
            text: The text to extract JSON from
            repair_info: List to append repair information to
            
        Returns:
            str: Manually constructed JSON
        """
        text = text.strip()
        repair_info.append("Starting manual JSON rebuilding")
        
        # First try a simple approach - fix unquoted keys
        # Convert any unquoted property names into quoted ones
        text = re.sub(r'(?:^|\{|\s|,)(\w+)(?=\s*:)', r'"\1"', text)
        repair_info.append("Added quotes to property names in manual rebuilding")
        
        # Try to parse directly after this simple fix
        try:
            return text
        except Exception:
            pass  # Continue with the more complex approach

        # Try to see if we have a simple key-value structure
        simple_kvp_pattern = r'\s*{\s*(.+?):\s*(.+?)\s*}\s*'
        kvp_match = re.search(simple_kvp_pattern, text, re.DOTALL)
        if kvp_match:
            try:
                key = kvp_match.group(1).strip()
                value = kvp_match.group(2).strip()
                
                # Force quotes around the key if not already quoted
                if not (key.startswith('"') and key.endswith('"')):
                    key = f'"{key}"'
                    
                # If value isn't a valid JSON literal, put quotes around it
                try:
                    json.loads(value)
                except:
                    if not (value.startswith('"') and value.endswith('"')):
                        value = f'"{value}"'
                        
                # Construct a minimal valid JSON object
                return f"{{{key}: {value}}}"
                
            except Exception as e:
                repair_info.append(f"Simple key-value extraction failed: {e}")

        # Try to extract the reasoning section
        reasoning_pattern = r'"?reasoning"?:\s*(?:"""|"|\'|\s*)(.*?)(?:"""|"|\'|\s*),\s*("?tasks"?|$)'
        reasoning_match = re.search(reasoning_pattern, text, re.DOTALL)
        
        # Try to extract the tasks section
        tasks_pattern = r'"?tasks"?:\s*\[(.*?)\]'
        tasks_match = re.search(tasks_pattern, text, re.DOTALL)
        
        if reasoning_match:
            # We found at least the reasoning part
            reasoning_text = reasoning_match.group(1).strip()
            
            # Clean up the reasoning text - replace newlines with spaces
            reasoning_text = re.sub(r'\s+', ' ', reasoning_text)
            
            # Construct a valid JSON object
            result = {
                "reasoning": reasoning_text,
                "tasks": []  # Default empty tasks
            }
            
            # If we also found tasks, try to parse them
            if tasks_match:
                tasks_text = tasks_match.group(1).strip()
                
                # Attempt to parse tasks
                # Split tasks by closing/opening braces with comma in between
                tasks_split = re.split(r'},\s*{', tasks_text)
                
                for i, task_text in enumerate(tasks_split):
                    # Add back the braces we removed during splitting
                    if not task_text.startswith('{'):
                        task_text = '{' + task_text
                    if not task_text.endswith('}'):
                        task_text = task_text + '}'
                        
                    # Clean up common issues
                    task_text = re.sub(r'(\w+):', r'"\1":', task_text)  # Quote keys
                    task_text = task_text.replace("'", '"')  # Replace single quotes with double quotes
                    
                    try:
                        # Try to parse this task
                        task_json = json.loads(task_text)
                        result['tasks'].append(task_json)
                        repair_info.append(f"Successfully parsed task {i+1}")
                    except json.JSONDecodeError:
                        # If we can't parse this task, add a minimal placeholder
                        result['tasks'].append({
                            "type": "placeholder",
                            "description": f"Failed to parse task {i+1}"
                        })
                        repair_info.append(f"Added placeholder for task {i+1}")
            
            # Convert the result back to JSON
            return json.dumps(result)
        else:
            # Last resort: try to extract any JSON-like structure
            # Look for patterns like {"key": "value"} or {key: value}
            json_pattern = r'{\s*(.*?)\s*}'
            json_match = re.search(json_pattern, text, re.DOTALL)
            
            if json_match:
                content = json_match.group(1).strip()
                
                # Check if we've got key-value pairs
                if ':' in content:
                    # Try to extract key-value pairs
                    pairs = []
                    for pair in re.split(r',\s*', content):
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Quote keys if they're not already
                            if not (key.startswith('"') and key.endswith('"')):
                                key = f'"{key}"'
                                
                            # Simple quoting for values that aren't objects/arrays
                            if not (value.startswith('{') or value.startswith('[') or 
                                    value.startswith('"') or value in ['true', 'false', 'null'] or
                                    re.match(r'^-?\d+(\.\d+)?$', value)):
                                value = f'"{value}"'
                                
                            pairs.append(f"{key}: {value}")
                    
                    return "{" + ", ".join(pairs) + "}"
                
            # If we couldn't extract anything useful, create a minimal valid JSON
            repair_info.append("Could not extract key components, creating minimal JSON")
            return '{"error": "JSON extraction failed", "original_text": "' + text.replace('"', '\\"') + '"}'

    def to_json(self):
        return json.dumps({
            "type": self.type,
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "seed": self.seed,
            "temperature": self.temperature,
            "object_id": self.object_id,
            "created": self.created,
            "name": self.name,
            "description": self.description
        })
    
    def __repr__(self):
        return f"<llm {self.type} {self.model_name} (object_id: {self.object_id})>"