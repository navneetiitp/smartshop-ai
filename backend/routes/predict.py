from flask import Blueprint, request, jsonify
from backend.utils.data_loader import get_dataframe
from backend.ml.predictor import predict_future_price

predict_bp = Blueprint("predict", __name__)

@predict_bp.route("/predict")
def predict():
    name = request.args.get("name", "").strip()
    days = request.args.get("days", type=int, default=30)
    days = max(7, min(days, 90))

    if not name:
        return jsonify({"error": "Product name required"}), 400

    df = get_dataframe()
    result = predict_future_price(name, df, days)
    result["product_name"] = name
    return jsonify(result)