import pandas as pd


def calculate_value_score(row: pd.Series, df: pd.DataFrame) -> float:
    """Deterministic 0-100 value score; it is not a third-party AI rating.

    Price is compared with the candidate set being displayed, while rating and
    review signal provide quality context. This avoids giving every unique
    product the same default price score.
    """
    prices = pd.to_numeric(df.get("price"), errors="coerce").dropna()
    if len(prices) >= 2:
        low = float(prices.quantile(0.10))
        high = float(prices.quantile(0.90))
        price = float(row.get("price", 0) or 0)
        if high > low:
            price_score = max(0.0, min(40.0, (high - price) / (high - low) * 40.0))
        else:
            price_score = 20.0
    else:
        price_score = 20.0

    rating = row.get("ratings_num")
    rating_score = (max(0.0, min(5.0, float(rating))) / 5.0) * 40.0 if pd.notna(rating) and float(rating) > 0 else 20.0

    sentiment = row.get("review_sentiment")
    if pd.notna(sentiment) and sentiment is not None:
        review_score = (max(0.0, min(5.0, float(sentiment))) / 5.0) * 20.0
    else:
        review = str(row.get("reviews", "")).lower()
        if "excellent" in review:
            review_score = 20.0
        elif "very good" in review:
            review_score = 16.0
        elif "good" in review:
            review_score = 13.0
        elif "average" in review or "decent" in review:
            review_score = 10.0
        elif "not satisfactory" in review or "poor" in review:
            review_score = 4.0
        else:
            review_score = 10.0

    return round(max(0.0, min(100.0, price_score + rating_score + review_score)), 1)


def calculate_ai_score(row: pd.Series, df: pd.DataFrame) -> float:
    # Backward-compatible function name for existing routes.
    return calculate_value_score(row, df)


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ai_score"] = df.apply(lambda row: calculate_value_score(row, df), axis=1)
    df["value_score"] = df["ai_score"]
    return df
