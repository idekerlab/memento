import anthropic
import google.generativeai as genai
from app.config import load_api_key
from app.utils.logging import (
    log_api_call, log_error, log_json_processing, 
    log_tool_use, format_object
)
import json
import re
import unicodedata

class LLM:
    def __init__(self, type=None, model_name="claude-3-7-sonnet-20250219",
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

        if self.type == 'Anthropic':
            try:
                return self.query_anthropic(context, prompt, tools=tools, tool_choice=tool_choice)  # Don't await here
            except Exception as e:
                raise Exception(f"Query failed: {str(e)}")
        elif self.type == 'Google':
            try:
                return self.query_gemini(context, prompt, tools=tools, tool_choice=tool_choice)
            except Exception as e:
                raise Exception(f"Query failed: {str(e)}")
        else:
            raise ValueError(f"Unsupported llm type: {self.type}")

    def query_gemini(self, context, prompt, tools=None, tool_choice=None):
        """Synchronous wrapper around Google Gemini API call"""
        key = load_api_key("GOOGLEAI_KEY")
        if not key:
            raise EnvironmentError("GOOGLEAI_KEY environment variable not set.")
            
        # Configure Gemini
        genai.configure(api_key=key)
        
        # Initialize model
        model = genai.GenerativeModel(self.model_name)
        
        # Log the API call
        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "content_length": len(context) + len(prompt),
            "has_tools": tools is not None
        }
        log_api_call(f"Gemini-{self.model_name}", "generate_content", params)
        
        try:
            # Combine context and prompt
            combined_text = f"{context}\n\n{prompt}"
            
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
            
            # Handle tools if they're provided
            if tools:
                # Convert OpenAI/Anthropic style tools to Gemini format
                gemini_tools = self._convert_tools_to_gemini_format(tools)
                
                # Call Gemini with tools
                response = model.generate_content(
                    combined_text,
                    generation_config=generation_config,
                    tools=gemini_tools
                )
            else:
                # Regular call without tools
                response = model.generate_content(
                    combined_text,
                    generation_config=generation_config
                )
            
            return response
                
        except Exception as e:
            error_obj = log_error("APIError", "Gemini API call failed", 
                                details={"model": self.model_name}, exc=e)
            raise Exception(f"Gemini API call failed: {str(e)}")
    
    def _convert_tools_to_gemini_format(self, tools):
        """Convert OpenAI/Anthropic style tools to Gemini format"""
        gemini_tools = []
        
        for tool in tools:
            if isinstance(tool, dict) and "type" in tool and tool["type"] == "function":
                if "function" in tool:
                    function_data = tool["function"]
                    
                    # Create Gemini tool format
                    gemini_tool = {
                        "function_declarations": [{
                            "name": function_data.get("name", ""),
                            "description": function_data.get("description", ""),
                            "parameters": function_data.get("parameters", {})
                        }]
                    }
                    gemini_tools.append(gemini_tool)
                else:
                    print(f"Skipping tool due to missing 'function' field: {tool}")
            else:
                print(f"Skipping tool with unsupported type: {tool}")
                
        return gemini_tools
    
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
            tool_names = []
            if tools:
                anthropic_tools = []
                for tool in tools:
                    if isinstance(tool, dict) and "type" in tool and tool["type"] == "function":
                        if "function" in tool:
                            # Extract function data directly
                            function_data = tool["function"]
                            
                            # Get tool name for logging
                            tool_name = function_data.get("name", "unnamed_tool")
                            tool_names.append(tool_name)
                            
                            # Create Anthropic tool format - directly copying fields
                            anthropic_tool = {
                                "name": tool_name,
                                "description": function_data.get("description", ""),
                                "input_schema": function_data.get("parameters", {})
                            }
                            anthropic_tools.append(anthropic_tool)
                        else:
                            log_error("ToolConversionError", "Missing 'function' field in tool", 
                                     details={"tool": format_object(tool)})
                    else:
                        log_error("ToolConversionError", "Unsupported tool type", 
                                 details={"tool": format_object(tool)})
                
                kwargs["tools"] = anthropic_tools
            
            # Format tool_choice correctly for Anthropic
            selected_tool = None
            if tool_choice:
                if isinstance(tool_choice, dict):
                    if "type" in tool_choice and tool_choice["type"] == "function":
                        # Convert from OpenAI format to Anthropic format
                        if "function" in tool_choice and "name" in tool_choice["function"]:
                            # Get the tool name for Anthropic format
                            tool_name = tool_choice["function"]["name"]
                            selected_tool = tool_name
                            
                            # Use the proper Anthropic format
                            kwargs["tool_choice"] = {"type": "tool", "name": tool_name}
                            log_tool_use(tool_name, "specified in tool_choice")
                        else:
                            # Use auto if we can't extract a name
                            kwargs["tool_choice"] = {"type": "auto"}
                            log_tool_use("auto", "defaulted to auto (no tool name)")
                    else:
                        # If it already has 'type' but not 'function', pass through
                        kwargs["tool_choice"] = tool_choice
                        if "name" in tool_choice:
                            selected_tool = tool_choice.get("name")
                            log_tool_use(selected_tool, "using provided tool_choice")
                else:
                    # If not a dict, convert to auto
                    kwargs["tool_choice"] = {"type": "auto"}
                    log_tool_use("auto", "defaulted to auto (non-dict tool_choice)")
            elif tools and len(tools) == 1 and len(anthropic_tools) == 1:
                # If there's only one tool and no explicit choice, use it
                tool_name = anthropic_tools[0]["name"]
                kwargs["tool_choice"] = {"type": "tool", "name": tool_name}
                selected_tool = tool_name
                log_tool_use(tool_name, "auto-selected (single tool)")
            
            # Log the API call
            params = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "content_length": len(context) + len(prompt),
                "tools": f"{len(tool_names)} tools: {', '.join(tool_names)}" if tool_names else "None",
                "tool_choice": selected_tool if selected_tool else "None"
            }
            log_api_call(f"Claude-{self.model_name}", "create", params)
            
            # Make the API call
            response = client.messages.create(**kwargs)
            return response
                
        except Exception as e:
            error_obj = log_error("APIError", "Anthropic API call failed", 
                                details={"model": self.model_name}, exc=e)
            raise Exception(f"Anthropic API call failed: {str(e)}")

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
        log_json_processing("query_and_parse_json", "started", {
            "model": f"{self.type}-{self.model_name}",
            "has_tools": tools is not None
        })
        
        try:
            # Make the API call
            response = await self.query(context, prompt, tools, tool_choice)
            
            # Check for tool use and extract text based on the LLM provider
            has_tool_use = False
            response_text = None
            
            # Handle Anthropic responses
            if self.type == 'Anthropic':
                if hasattr(response, 'content') and len(response.content) > 0:
                    content_type = type(response.content[0]).__name__
                    log_json_processing("extract_content", "processing", {
                        "content_type": content_type
                    })
                    
                    # Detect ToolUseBlock directly
                    if content_type == 'ToolUseBlock':
                        has_tool_use = True
                        # Extract tool name and input
                        tool_name = response.content[0].name
                        tool_input = response.content[0].input
                        log_tool_use(tool_name, "received_response")
                        return tool_input, f"Tool response from {tool_name}"
                    
                    # Try to access tool_use attribute if available
                    elif hasattr(response.content[0], 'tool_use') and response.content[0].tool_use:
                        tool_use = response.content[0].tool_use
                        has_tool_use = True
                        log_tool_use(tool_use.name, "received_response")
                        return tool_use.input, "Tool response (no JSON parsing needed)"
                
                # If there's no tool use, extract text content
                if not has_tool_use:
                    # For TextBlock type content
                    if hasattr(response, 'content') and hasattr(response.content[0], 'text'):
                        response_text = response.content[0].text
                    # For direct content
                    elif hasattr(response, 'text'):
                        response_text = response.text
            
            # Handle Google Gemini responses
            elif self.type == 'Google':
                log_json_processing("extract_content", "processing", {
                    "response_type": type(response).__name__
                })
                
                # Check for function calling response
                if hasattr(response, 'candidates') and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    
                    # Check for function calls in the candidate
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            # Check for function call
                            if hasattr(part, 'function_call'):
                                has_tool_use = True
                                tool_name = part.function_call.name
                                tool_args = part.function_call.args
                                log_tool_use(tool_name, "received_response")
                                return tool_args, f"Tool response from {tool_name}"
                    
                    # Extract text if no tool use found
                    if not has_tool_use and hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                response_text = part.text
                                break
                
                # Try direct text attribute as fallback
                if not response_text and hasattr(response, 'text'):
                    response_text = response.text
            
            # If we couldn't extract text from any known format, log error and raise
            if not response_text:
                error_obj = log_error("ResponseError", "Could not find text content in response", 
                                     details={"response_type": type(response).__name__,
                                              "attributes": dir(response)})
                raise ValueError("Could not find text content in response - unsupported response format")
            
            log_json_processing("text_extraction", "completed", {
                "text_length": len(response_text),
                "preview": response_text[:50] + "..." if len(response_text) > 50 else response_text
            })
            
            # First attempt to parse as-is
            try:
                parsed_json = json.loads(response_text)
                log_json_processing("json_parse", "success", {
                    "method": "direct_parse"
                })
                return parsed_json, None  # No repair needed
                
            except json.JSONDecodeError as e:
                log_json_processing("json_parse", "failed", {
                    "error": str(e),
                    "position": e.pos,
                    "context": response_text[max(0, e.pos-20):min(len(response_text), e.pos+20)]
                })
                
                # Try to repair the JSON
                repair_info = []
                fixed_json_text = self._repair_json(response_text, repair_info)
                
                # Try to parse the repaired JSON
                try:
                    parsed_json = json.loads(fixed_json_text)
                    log_json_processing("json_repair", "success", {
                        "method": "standard_repair",
                        "repair_steps": len(repair_info)
                    })
                    return parsed_json, "\n".join(repair_info)
                        
                except json.JSONDecodeError as secondary_e:
                    log_json_processing("json_repair", "failed", {
                        "method": "standard_repair",
                        "error": str(secondary_e)
                    })
                    
                    # If we still can't parse, try direct simple replacement of triple quotes
                    repair_info.append("Attempting simple triple quote fix...")
                    
                    # Replace triple quotes directly with single quotes
                    simple_fixed = response_text.replace('"""', '"')
                    
                    try:
                        parsed_json = json.loads(simple_fixed)
                        repair_info.append("Simple triple quote replacement worked")
                        log_json_processing("json_repair", "success", {
                            "method": "triple_quote_fix"
                        })
                        return parsed_json, "\n".join(repair_info)
                    except json.JSONDecodeError:
                        log_json_processing("json_repair", "failed", {
                            "method": "triple_quote_fix",
                            "error": str(secondary_e)
                        })
                        
                        # If still fails, try the manual approach
                        repair_info.append("Attempting manual JSON building...")
                        manual_json = self._build_json_manually(response_text, repair_info)
                        
                        try:
                            parsed_json = json.loads(manual_json)
                            log_json_processing("json_repair", "success", {
                                "method": "manual_building"
                            })
                            return parsed_json, "\n".join(repair_info)
                        except json.JSONDecodeError:
                            # If all repairs fail, raise the original error with repair context
                            error_msg = f"JSON repair failed. Original error: {str(e)}."
                            log_error("JSONRepairError", "All repair methods failed", {
                                "original_error": str(e),
                                "repair_attempts": len(repair_info)
                            })
                            raise json.JSONDecodeError(
                                error_msg, 
                                doc=response_text, 
                                pos=e.pos
                            )
                
        except Exception as e:
            if isinstance(e, json.JSONDecodeError):
                # Already logged above
                raise  # Re-raise JSON errors as they've already been handled
            
            log_error("QueryParseError", "Error querying LLM or parsing response", 
                     exc=e)
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
