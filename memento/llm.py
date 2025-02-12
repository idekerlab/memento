import anthropic
from config import load_api_key
import json

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

    async def query(self, context, prompt):
        """Main query method that routes to appropriate model"""
        self.max_tokens = int(self.max_tokens)
        self.temperature = float(self.temperature)
        self.seed = int(self.seed)

        # For now just handle Anthropic since that's what we're testing
        if self.type == 'Anthropic':
            try:
                return self.query_anthropic(context, prompt)  # Don't await here
            except Exception as e:
                raise Exception(f"Query failed: {str(e)}")
        else:
            raise ValueError(f"Unsupported llm type: {self.type}")

    def query_anthropic(self, context, prompt):
        """Synchronous wrapper around Anthropic API call"""
        key = load_api_key("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
            
        client = anthropic.Anthropic(api_key=key)
        
        try:
            response = client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"{context}\n\n{prompt}"
                    }
                ]
            )
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Anthropic API call failed: {str(e)}")

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