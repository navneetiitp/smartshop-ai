import pandas as pd
import numpy as np
import os
import re

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/products.csv")
PLACEHOLDER = "https://placehold.co/400x300/1e293b/94a3b8?text=No+Image"

REVIEW_SENTIMENT = {
    "Excellent performance and premium build quality": 5,
    "Very good laptop with solid performance": 4,
    "Average performance, decent for daily use": 3,
    "Performance is not satisfactory": 2,
    "No reviews available": None
}


_BRANDS = ("dell", "hp", "apple", "lenovo", "asus", "acer", "msi", "microsoft", "samsung", "razer", "lg", "gigabyte", "framework")

def _clean_text(value, fallback="N/A") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "n/a", "not available"}:
        return fallback
    return text

def _clean_product_name(value) -> str:
    text = _clean_text(value)
    # Remove accidental repeated manufacturer prefixes such as
    # "Dell Dell Inspiron" or "Apple Apple MacBook" while preserving the model.
    for brand in _BRANDS:
        pattern = rf"^(\s*{re.escape(brand)})(?:\s+{re.escape(brand)})+(?=\s|$)"
        text = re.sub(pattern, brand.title() if brand != "hp" else "HP", text, flags=re.I)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

def _clean_description(value) -> str:
    text = _clean_text(value)
    # The source occasionally duplicates the vendor family name (e.g.
    # "Processor: Intel Intel Core i7"). Keep the actual specification once.
    text = re.sub(r"\b(Intel|AMD|Apple|Qualcomm)\s+\1\b", r"\1", text, flags=re.I)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text

def _normalize_website(value) -> str:
    text = _clean_text(value, "Unknown")
    aliases = {
        "amazon.com": "Amazon", "amazon": "Amazon",
        "bestbuy": "BestBuy", "best buy": "BestBuy",
        "flipkart": "Flipkart", "ebay": "eBay", "ebay.com": "eBay",
    }
    return aliases.get(text.lower(), text)

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

    # Normalize user-facing text and retailer names so the UI does not expose
    # obvious source-data artifacts such as "Dell Dell" or "Intel Intel".
    df["product_name"] = df["product_name"].apply(_clean_product_name)
    df["product_description"] = df["product_description"].apply(_clean_description)
    df["website"] = df["website"].apply(_normalize_website)
    for col in ["reviews", "ratings"]:
        if col in df.columns:
            df[col] = df[col].apply(_clean_text)

    # Validate historical links before exposing them to the browser.
    # Only normal HTTP(S) URLs are allowed; malformed or script-like values
    # become non-clickable placeholders.
    if "product_link" in df.columns:
        def _safe_link(value):
            text = str(value or "").strip()
            return text if re.match(r"^https?://[^\s]+$", text, flags=re.I) else "#"
        df["product_link"] = df["product_link"].apply(_safe_link)

    df = df.reset_index(drop=True)
    df["id"] = df.index

    _df_cache = df
    return df.copy()
