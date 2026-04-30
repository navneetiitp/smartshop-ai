from flask import Blueprint, request, jsonify
from backend.utils.data_loader import get_dataframe
from backend.ml.ai_score import calculate_ai_score
from backend.ml.summarizer import generate_summary
import pandas as pd

summary_bp = Blueprint("summary", __name__)

@summary_bp.route("/summary/<int:product_id>")
def summary(product_id):
    df = get_dataframe()
    row = df[df["id"] == product_id]

    if row.empty:
        return jsonify({"error": "Product not found"}), 404

    row = row.iloc[0]
    ai_score = calculate_ai_score(row, df)
    text = generate_summary(
        product_name=row["product_name"],
        description=row["product_description"],
        price=int(row["price"]),
        rating=float(row["ratings_num"]) if pd.notna(row["ratings_num"]) else None,
        review=row["reviews"],
        ai_score=ai_score,
        website=row["website"]
    )
    return jsonify({"summary": text, "ai_score": ai_score})