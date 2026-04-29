import pandas as pd
import numpy as np


def calculate_ai_score(row: pd.Series, df: pd.DataFrame) -> float:
    """
    AI Score (0-100) — weighted combination aligned with price+rating+reviews:

    Weight breakdown:
      - Price competitiveness  (40%) — lower price vs peers = higher score
      - Rating score           (30%) — numeric rating 1-5
      - Review sentiment       (20%) — mapped to 1-5 scale
      - Recency score          (10%) — how fresh the listing is

    This scoring is intentionally dominated by price (40%) + quality (30%)
    so the highest AI score reliably matches the best overall value.
    """

    # -- Price competitiveness (40%) --
    same_product = df[df["product_name"] == row["product_name"]]
    if len(same_product) > 1:
        min_price = same_product["price"].min()
        max_price = same_product["price"].max()
        if max_price > min_price:
            price_score = ((max_price - row["price"]) / (max_price - min_price)) * 40
        else:
            price_score = 20.0
    else:
        price_score = 20.0

    # -- Rating score (30%) --
    rating = row.get("ratings_num")
    if pd.notna(rating) and rating > 0:
        rating_score = (min(float(rating), 5.0) / 5.0) * 30
    else:
        rating_score = 15.0

    # -- Review sentiment score (20%) --
    sentiment = row.get("review_sentiment")
    if pd.notna(sentiment) and sentiment is not None:
        sentiment_score = (min(float(sentiment), 5.0) / 5.0) * 20
    else:
        review = str(row.get("reviews", "")).lower()
        if "excellent" in review:
            sentiment_score = 20.0
        elif "very good" in review:
            sentiment_score = 16.0
        elif "good" in review:
            sentiment_score = 13.0
        elif "average" in review or "decent" in review:
            sentiment_score = 10.0
        elif "not satisfactory" in review or "poor" in review:
            sentiment_score = 4.0
        else:
            sentiment_score = 10.0

    # -- Recency score (10%) --
    try:
        date = pd.to_datetime(row["date"])
        now = pd.Timestamp.now()
        days_old = max(0, (now - date).days)
        recency_score = max(0.0, (1 - days_old / 365)) * 10
    except Exception:
        recency_score = 5.0

    total = price_score + rating_score + sentiment_score + recency_score
    return round(min(max(total, 0.0), 100.0), 1)


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ai_score"] = df.apply(lambda row: calculate_ai_score(row, df), axis=1)
    return df
