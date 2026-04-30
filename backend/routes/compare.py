from flask import Blueprint, request, jsonify
from backend.utils.data_loader import get_dataframe
from backend.ml.ai_score import score_dataframe
import pandas as pd

compare_bp = Blueprint("compare", __name__)


def _price_explanation(best_price_item: dict, best_value_item: dict, listings: list) -> str:
    if not listings:
        return "Lowest price among all stores."

    prices = [l["price"] for l in listings]
    max_price = max(prices)
    savings = max_price - best_price_item["price"]

    if savings > 0:
        return (
            f"Lowest price among all stores. "
            f"Save ₹{savings:,} compared to the most expensive listing."
        )
    return "Lowest price among all stores."


def _value_explanation(best_value_item: dict, listings: list) -> str:
    score = best_value_item.get("ai_score", 0)
    rating = best_value_item.get("ratings_num")

    parts = []
    if rating and rating > 0:
        parts.append(f"rated {rating:.1f}★")

    review = str(best_value_item.get("reviews", "")).lower()
    if "excellent" in review:
        parts.append("excellent reviews")
    elif "very good" in review:
        parts.append("very good reviews")

    quality = ", ".join(parts) if parts else "solid quality indicators"
    return (
        f"Best overall choice based on price, rating, and reviews. "
        f"AI Score {score:.0f}/100 — {quality}."
    )


@compare_bp.route("/compare")
def compare():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Product name required"}), 400

    df = get_dataframe()
    df = score_dataframe(df)

    mask = df["product_name"].str.lower().str.contains(name.lower(), na=False)
    matches = df[mask]

    if matches.empty:
        return jsonify({"error": "No products found", "name": name}), 404

    results = []
    for _, row in matches.iterrows():
        results.append({
            "id":           int(row["id"]),
            "product_name": str(row["product_name"]) if pd.notna(row["product_name"]) else "N/A",
            "price":        int(row["price"]),
            "ratings":      str(row["ratings"]) if pd.notna(row["ratings"]) else "N/A",
            "ratings_num":  float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
            "reviews":      str(row["reviews"]) if pd.notna(row["reviews"]) else "N/A",
            "product_link": str(row["product_link"]) if pd.notna(row["product_link"]) else "#",
            "image_link":   _safe_image(row.get("image_link")),
            "website":      str(row["website"]) if pd.notna(row["website"]) else "N/A",
            "ai_score":     float(row["ai_score"]),
        })

    results.sort(key=lambda x: x["price"])

    best_deal_item = None
    best_value_item = None

    if results:
        min_price = results[0]["price"]
        max_price = results[-1]["price"]

        cheapest = [r for r in results if r["price"] == min_price]
        best_deal_item = max(cheapest, key=lambda x: x.get("ai_score", 0))

        best_value_item = max(results, key=lambda x: (x.get("ai_score", 0), -x["price"]))

        same = best_deal_item["id"] == best_value_item["id"]

        for r in results:
            is_deal  = r["id"] == best_deal_item["id"]
            is_value = r["id"] == best_value_item["id"]
            if same and is_deal:
                r["badge"] = "both"
            elif is_deal:
                r["badge"] = "best_deal"
            elif is_value:
                r["badge"] = "best_value"
            else:
                r["badge"] = None

        savings = max_price - min_price

        best_deal_out = dict(best_deal_item)
        best_deal_out["is_best_deal"]       = True
        best_deal_out["badge"]              = "both" if same else "best_deal"
        best_deal_out["deal_explanation"]   = _price_explanation(best_deal_item, best_value_item, results)

        best_value_out = dict(best_value_item)
        best_value_out["is_best_value"]     = True
        best_value_out["badge"]             = "both" if same else "best_value"
        best_value_out["value_explanation"] = _value_explanation(best_value_item, results)

    else:
        best_deal_out = None
        best_value_out = None
        savings = 0

    return jsonify({
        "name":       name,
        "listings":   results,
        "best_deal":  best_deal_out,
        "best_value": best_value_out,
        "price_range": {
            "min":     results[0]["price"] if results else 0,
            "max":     results[-1]["price"] if results else 0,
            "savings": savings if results else 0,
        }
    })


def _safe_image(url) -> str:
    placeholder = "https://placehold.co/400x300/1e293b/94a3b8?text=No+Image"
    if not url or str(url).strip() in ("", "nan", "None", "Not Available", "N/A"):
        return placeholder
    url = str(url).strip()
    if not url.startswith("http"):
        return placeholder
    return url