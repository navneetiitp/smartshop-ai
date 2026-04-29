from flask import Blueprint, request, jsonify
from utils.data_loader import get_dataframe
from ml.ai_score import score_dataframe
import pandas as pd

search_bp = Blueprint("search", __name__)


@search_bp.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    website = request.args.get("website", "all")
    sort_by = request.args.get("sort", "ai_score")
    min_price = request.args.get("min_price", type=int, default=0)
    max_price = request.args.get("max_price", type=int, default=9999999)
    page = request.args.get("page", type=int, default=1)
    per_page = request.args.get("per_page", type=int, default=20)

    df = get_dataframe()

    # Filter by query
    if query:
        mask = (
            df["product_name"].str.lower().str.contains(query, na=False) |
            df["product_description"].str.lower().str.contains(query, na=False)
        )
        df = df[mask]

    # Filter by website
    if website and website != "all":
        df = df[df["website"].str.lower() == website.lower()]

    # Filter by price
    df = df[(df["price"] >= min_price) & (df["price"] <= max_price)]

    if df.empty:
        return jsonify({"results": [], "total": 0, "page": page, "pages": 0})

    # Calculate AI scores
    df = score_dataframe(df)

    # Sort
    sort_map = {
        "ai_score": ("ai_score", False),
        "price_asc": ("price", True),
        "price_desc": ("price", False),
        "rating": ("ratings_num", False),
    }
    sort_col, asc = sort_map.get(sort_by, ("ai_score", False))
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=asc, na_position="last")

    total = len(df)
    pages = (total + per_page - 1) // per_page
    df_page = df.iloc[(page - 1) * per_page: page * per_page]

    results = []
    for _, row in df_page.iterrows():
        results.append({
            "id": int(row["id"]),
            "product_name": row["product_name"],
            "product_description": row["product_description"],
            "price": int(row["price"]),
            "ratings": row["ratings"],
            "ratings_num": float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
            "reviews": row["reviews"],
            "product_link": row["product_link"],
            "image_link": row["image_link"],
            "website": row["website"],
            "date": str(row["date"]),
            "ai_score": float(row["ai_score"]),
        })

    return jsonify({"results": results, "total": total, "page": page, "pages": pages})


@search_bp.route("/product/<int:product_id>")
def get_product(product_id):
    df = get_dataframe()
    df = score_dataframe(df)
    row = df[df["id"] == product_id]
    if row.empty:
        return jsonify({"error": "Product not found"}), 404
    row = row.iloc[0]
    return jsonify({
        "id": int(row["id"]),
        "product_name": row["product_name"],
        "product_description": row["product_description"],
        "price": int(row["price"]),
        "ratings": row["ratings"],
        "ratings_num": float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
        "reviews": row["reviews"],
        "product_link": row["product_link"],
        "image_link": row["image_link"],
        "website": row["website"],
        "date": str(row["date"]),
        "ai_score": float(row["ai_score"]),
    })
