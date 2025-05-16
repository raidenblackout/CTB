from api_client.OllamaClient import OllamaClient
try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not found. Some functions might not work as expected.")
    print("Install with: pip install openai")
    OpenAI = None # type: ignore


class SentimentAnalyzer:
    """
    A class to analyze sentiment of text using LLMs.
    """

    def __init__(self, llm_method="openai", api_client=None):
        self.llm_method = llm_method
        self.api_client = api_client or OllamaClient()


    def analyze_sentiment(self, text_to_analyze, target_coin):
        """
        Analyzes the sentiment of the given text using the specified LLM method.
        """
        return self.get_sentiment_signal(text_to_analyze, target_coin, self.llm_method)
    
    def get_sentiment_signal(self, text_to_analyze, target_coin, llm_method="openai"):
        """
        Gets a sentiment signal from the LLM for the given text.
        Returns a sentiment string like "Positive", "Negative", "Neutral", or None.
        """
        # You might want to add more context or few-shot examples for better results
        system_prompt = (
            "You are a financial sentiment analyst. "
            "Analyze the sentiment of the following crypto news headline based on the given crypto. "
            "Classify the sentiment strictly as 'Positive', 'Negative', or 'Neutral'. "
            "Do not add any other commentary or explanation. Only provide the classification."
        )
        user_prompt_content = f"News Headline: \"{text_to_analyze}\""
        target_coin = "Target Coin: " + target_coin
        user_prompt_content += f"\n{target_coin}\n\n"

        llm_response = None
        if llm_method == "openai" and OpenAI is not None:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
            ]
            llm_response = self.api_client.query_ollama_openai_compatible(messages)
        elif llm_method == "direct":
            # For direct /api/generate, you often combine system and user prompt
            full_prompt = f"{system_prompt}\n\nUser: {user_prompt_content}\nAssistant (Sentiment Classification Only):"
            llm_response = self.api_client.query_ollama_direct(full_prompt)
        else:
            print(f"Unknown LLM method: {llm_method} or OpenAI library missing.")
            return None

        if llm_response:
            print(f"  LLM Raw Response: '{llm_response}'")
            # Basic parsing (can be improved with regex or more robust checks)
            response_lower = llm_response.lower()
            if "positive" in response_lower:
                return "Positive"
            elif "negative" in response_lower:
                return "Negative"
            elif "neutral" in response_lower:
                return "Neutral"
            else:
                print(f"  Could not parse sentiment from LLM response: '{llm_response}'")
                return "Uncertain" # Or None, depending on how you want to handle
        return None