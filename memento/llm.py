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
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
                
            response = client.messages.create(**kwargs)
            return response
                
        except Exception as e:
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
        try:
            # Make the API call
            response = await self.query(context, prompt, tools, tool_choice)
            
            # Extract the response text
            response_text = response.content[0].text if hasattr(response, 'content') else None
            
            if not response_text:
                raise ValueError("No text content found in response")
            
            # First attempt to parse as-is
            try:
                parsed_json = json.loads(response_text)
                return parsed_json, None  # No repair needed
                
            except json.JSONDecodeError as e:
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
        
        # Fix 2: Handle single quotes within already quoted strings
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
        
        # Fix 3: Handle missing quotes around property names
        unquoted_key_pattern = r'(\s*)(\w+)(\s*):(\s*)'
        matches = re.findall(unquoted_key_pattern, text)
        for match in matches:
            full = ''.join(match)
            key = match[1]
            replacement = f'{match[0]}"{key}"{match[2]}:{match[3]}'
            text = text.replace(full, replacement, 1)  # Replace only the first occurrence
            repair_info.append(f"Added quotes around property name: {key}")
        
        # Fix 4: Handle trailing commas in arrays/objects
        text = re.sub(r',(\s*[\]}])', r'\1', text)
        if ',' in original_text and re.search(r',\s*[\]}]', original_text):
            repair_info.append("Removed trailing commas")
        
        # Fix 5: Handle newlines in string literals more carefully
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
        
        # Fix 6: Remove control characters
        control_chars = [chr(i) for i in range(32) if i != 10 and i != 13 and i != 9]  # exclude newline, CR, tab
        for char in control_chars:
            if char in text:
                text = text.replace(char, '')
                repair_info.append(f"Removed control character: '\\x{ord(char):02x}'")
                
        # Fix 7: Normalize Unicode (handle special quotation marks, etc.)
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
        
        # Try to extract the reasoning section
        reasoning_pattern = r'"reasoning":\s*(?:"""|")(.*?)(?:"""|")\s*,'
        reasoning_match = re.search(reasoning_pattern, text, re.DOTALL)
        
        # Try to extract the tasks section
        tasks_pattern = r'"tasks":\s*\[(.*?)\]\s*}'
        tasks_match = re.search(tasks_pattern, text, re.DOTALL)
        
        if reasoning_match and tasks_match:
            # Got both parts, now rebuild
            reasoning_text = reasoning_match.group(1).strip()
            tasks_text = tasks_match.group(1).strip()
            
            # Clean up the reasoning text - replace newlines with spaces
            reasoning_text = re.sub(r'\s+', ' ', reasoning_text)
            
            # Construct a valid JSON object
            result = {
                "reasoning": reasoning_text,
                "tasks": []  # We'll parse tasks individually
            }
            
            # Attempt to parse tasks
            # This is very complex to do properly, so we'll use a simple approach
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
                task_text = task_text.replace("'", "\\'")  # Escape single quotes
                
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
            # If we couldn't extract the main components, create a minimal valid JSON
            repair_info.append("Could not extract key components, creating minimal JSON")
            return '{"reasoning": "Extraction failed", "tasks": []}'

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