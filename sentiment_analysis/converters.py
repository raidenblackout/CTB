# --- Convert Sentiment to Trading Signal ---
def sentiment_to_trading_signal(sentiment):
    """
    Converts sentiment string to a numerical trading signal.
    +1 for Buy (Positive)
    -1 for Sell (Negative)
     0 for Hold (Neutral/Uncertain)
    """
    if sentiment == "Positive":
        return 1  # Buy signal
    elif sentiment == "Negative":
        return -1 # Sell signal
    else: # Neutral or Uncertain
        return 0  # Hold signal