import time
from api_client.OllamaClient import OllamaClient
from sentiment_analysis.converters import sentiment_to_trading_signal
from sentiment_analysis.sentiment_analyzer import SentimentAnalyzer
from crypto_news_aggregator.main import get_top_recent_articles

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not found. Some functions might not work as expected.")
    print("Install with: pip install openai")
    OpenAI = None # type: ignore

# --- Main Loop for Generating Signals ---
if __name__ == "__main__":
    # Initialize the API client
    api_client = OllamaClient()  # Adjust the base URL as needed
    sentiment_analyzer = SentimentAnalyzer(llm_method="openai", api_client=api_client)
    # --- Simulate fetching news headlines for different coins ---
    # In a real bot, you'd fetch these from an API (NewsAPI, CryptoPanic, Twitter, etc.)
    news_feed = get_top_recent_articles(num_articles=100)  # Fetch top recent articles

    print("Starting LLM Signal Generator...\n")
    # Choose your preferred method: "openai" (recommended) or "direct"
    LLM_QUERY_METHOD = "openai" if OpenAI is not None else "direct"
    print(f"Using LLM Query Method: {LLM_QUERY_METHOD}\n")


    for item in news_feed:
        coins = item.related_coins
        headline = item.title
        content = item.content_snippet if item.content_snippet else headline  # Fallback to title if no content
        # Assuming the first coin is the primary one for the headline
        for coin in coins:
            print(f"Processing: {headline} for {coin}")
            sentiment_label = sentiment_analyzer.get_sentiment_signal(content, coin, llm_method=LLM_QUERY_METHOD)

            if sentiment_label:
                trading_signal = sentiment_to_trading_signal(sentiment_label)
                print(f"    Sentiment: {headline}\n    Trading Signal: {trading_signal} for {coin}\n")
            else:
                print(f"    Could not determine sentiment for {coin}.\n")


    print("Signal generation finished.")