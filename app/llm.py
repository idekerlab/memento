from openai import OpenAI, APIError, APIConnectionError, InternalServerError
import time
from groq import Groq
import google.generativeai as genai
import requests
from app.config import load_api_key, load_local_server_url

class LLM:
    def __init__(self, type=None, model_name=None,
                 max_tokens=None, seed=None, temperature=None,
                 name=None, description=None):
        self.type = type
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.seed = seed
        self.temperature = temperature
        self.name = name
        self.description = description

    def query(self, context, prompt):
        self.max_tokens = int(self.max_tokens)
        self.temperature = float(self.temperature)
        self.seed = int(self.seed)
        if self.type == 'OpenAI':
            return self.query_openai(context, prompt)
        elif self.type == 'Groq':
            return self.query_groq(context, prompt)
        elif self.type == 'GoogleAI':
            return self.query_google_model(context, prompt)
        elif self.type == 'LocalModel':
            return self.query_local_model(context, prompt)
        else:
            raise ValueError(f"Unsupported llm type: {self.type}")

    def query_openai(self, context, prompt):
        key = load_api_key("OPENAI_API_KEY")
        if not key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
        client = OpenAI(api_key=key)
        backoff_time = 10
        retries = 0
        max_retries = 5
        while retries < max_retries:
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": context},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    n=1,
                    stop=None,
                    seed=self.seed,
                    temperature=self.temperature
                )
                response_content = response.choices[0].message.content.strip()
                return response_content
            except APIConnectionError:
                print(f"AIP connection error, retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
                retries += 1
                backoff_time *= 2
            except InternalServerError:
                print(f"Server issue detected, retrying in {backoff_time} seconds...")
                time.sleep(backoff_time)
                retries += 1
                backoff_time *= 2
            except APIError as e:
                raise Exception(f"API error occurred: {e}")
            except Exception as e:
                raise Exception(f"An unexpected error occurred: {e}")
        else:
            raise Exception(f"Error: Max retries exceeded. Last exception: {e}")

    def query_groq(self, context, prompt):
        key = load_api_key("GROQ_API_KEY")
        if not key:
            raise EnvironmentError("GROQ_API_KEY environment variable not set.")
        client = Groq(api_key=key)
        backoff_time = 10
        retries = 0
        max_retries = 5
        while retries < max_retries:
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": context},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    stop=None,
                    temperature=self.temperature,
                )
                response_content = response.choices[0].message.content.strip()
                return response_content
            except requests.exceptions.RequestException as e:
                if e.response is not None and e.response.status_code in [500, 502, 503]:
                    print(f"Server issue detected (status code {e.response.status_code}), retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    retries += 1
                    backoff_time *= 2
                else:
                    raise Exception(f"Request error occurred: {e}")
            except Exception as e:
                raise Exception(f"An unexpected error occurred: {e}")
        raise Exception(f"Error: Max retries exceeded. Last exception: {e}")

    def query_google_model(self, context, prompt):
        key = load_api_key("GOOGLEAI_KEY")
        if not key:
            raise EnvironmentError("GOOGLEAI_KEY environment variable not set.")
        genai.configure(api_key=key)
        available_models = [m.name.split('/')[1] for m in genai.list_models()]
        if self.model_name not in available_models:
            raise ValueError(f"Unsupported model name: {self.model_name}, available models are: {available_models}")
        model = genai.GenerativeModel(self.model_name)
        messages = [
            {'role': 'model', 'parts': context},
            {'role': 'user', 'parts': prompt}
        ]
        try:
            response = model.generate_content(
                messages,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature
                )
            )
            response_content = response.text
            return response_content
        except Exception as e:
            raise Exception(f"Google model error occurred: {e}")

    def query_local_model(self, context, prompt):
        url = load_local_server_url()
        if not url:
            raise EnvironmentError("LOCAL_MODEL_HOST URL environment variable not set.")
        if self.model_name not in ['mistral:7b', 'mixtral:latest', 'mixtral:instruct', 'llama2:7b', 'llama2:latest']:
            raise ValueError(f"Unsupported model name: {self.model_name}, supported models are: mistral:7b, mixtral:latest, mixtral:instruct, llama2:7b, llama2:latest")
        backoff_time = 10
        retries = 0
        max_retries = 5
        while retries < max_retries:
            try:
                response = requests.post(url, json={
                    "model": self.model_name,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": context},
                        {"role": "user", "content": prompt}
                    ],
                    "options": {
                        "seed": self.seed,
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                }, timeout=120)
                if response.status_code == 200:
                    output = response.json()
                    analysis = output['message']['content']
                    return analysis
            except requests.exceptions.RequestException as e:
                if e.response is not None and e.response.status_code in [500, 502, 503]:
                    print(f"Server issue detected (status code {e.response.status_code}), retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    retries += 1
                    backoff_time *= 2
                else:
                    raise Exception(f"Request error occurred: {e}")
            except Exception as e:
                raise Exception(f"An unexpected error occurred: {e}")
        raise Exception(f"Error: Max retries exceeded. Last exception: {e}")

    def __repr__(self):
        return f"<LLM {self.type} {self.model_name}>"