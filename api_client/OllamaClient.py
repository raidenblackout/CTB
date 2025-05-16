import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not found. Some functions might not work as expected.")
    print("Install with: pip install openai")
    OpenAI = None # type: ignore

class OllamaClient:
    """
    OllamaClient is a class to interact with the Ollama API.
    It provides methods to query the API using both direct and OpenAI compatible endpoints.
    """

    def __init__(self, api_base_url=None, model="mistral:latest"):
        self.api_base_url = api_base_url or os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434")
        self.model = model
        self.openai_compatible_endpoint = f"{self.api_base_url}/v1/chat/completions"

        print(f"Using Ollama API base URL: {self.api_base_url}")
        print(f"Using model: {self.model}")


    def query_ollama_direct(self, prompt, temperature=0.2, max_tokens=100):
        """ 
        Direct API Query

        Args:
            - prompt (str): The prompt to send to the model.
            - temperature (float): The temperature for the model's response.
            - max_tokens (int): The maximum number of tokens to generate in the response.
        Returns:
            - str: The model's response as a string.
        """
        api_url = f"{self.api_base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Set to False to get the full response at once
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens # Corresponds to max_tokens
            }
        }
        try:
            response = requests.post(api_url, json=payload, timeout=60) # Increased timeout
            response.raise_for_status()  # Raise an exception for bad status codes
            # The response from /api/generate when stream=False gives the full response in 'response' key
            return response.json().get("response", "").strip()
        except requests.exceptions.RequestException as e:
            print(f"Error querying Ollama (direct): {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from Ollama (direct): {e} - Response: {response.text}")
        return None
    
    
    def query_ollama_openai_compatible(self, prompt_messages, temperature=0.2, max_tokens=100):
        """
        Queries Ollama using the OpenAI compatible /v1/chat/completions endpoint.
        prompt_messages should be a list of dictionaries, e.g., [{"role": "user", "content": "Your prompt"}]
        """
        if OpenAI is None:
            print("OpenAI library is required for query_ollama_openai_compatible function.")
            return None

        client = OpenAI(
            base_url=self.api_base_url + "/v1", # Point to your Ollama /v1 endpoint
            api_key="ollama",  # Required but not used by Ollama for authentication
        )
        try:
            chat_completion = client.chat.completions.create(
                model=self.model,
                messages=prompt_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error querying Ollama (OpenAI compatible): {e}")
            return None