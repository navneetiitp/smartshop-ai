import pandas as pd
import numpy as np
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/products.csv")
PLACEHOLDER = "https://placehold.co/400x300/1e293b/94a3b8?text=No+Image"

REVIEW_SENTIMENT = {
    "Excellent performance and premium build quality": 5,
    "Very good laptop with solid performance": 4,
    "Average performance, decent for daily use": 3,
    "Performance is not satisfactory": 2,
    "No reviews available": None
}

_df_cache = None


def _clean_image(url) -> str:
    """Return a valid image URL or the placeholder."""
    if url is None:
        return PLACEHOLDER
    url = str(url).strip()
    if url.lower() in ("", "nan", "none", "not available", "n/a", "na"):
        return PLACEHOLDER
    if not url.startswith("http"):
        return PLACEHOLDER
    return url


def get_dataframe() -> pd.DataFrame:
    global _df_cache
    if _df_cache is not None:
        return _df_cache.copy()

    df = pd.read_csv(DATA_PATH)

    # Clean ratings
    df["ratings_num"] = pd.to_numeric(df["ratings"], errors="coerce")

    # Sentiment
    df["review_sentiment"] = df["reviews"].map(REVIEW_SENTIMENT)

    # Clean price
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    df["price"] = df["price"].astype(int)

    # Normalize date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Safe image links
    df["image_link"] = df["image_link"].apply(_clean_image)

    # Fill missing text fields with N/A
    for col in ["product_name", "product_description", "reviews", "ratings", "website"]:
        if col in df.columns:
            df[col] = df[col].fillna("N/A")

    # Fill missing product_link
    if "product_link" in df.columns:
        df["product_link"] = df["product_link"].fillna("#")

    df = df.reset_index(drop=True)
    df["id"] = df.index

    _df_cache = df
    return df.copy()
