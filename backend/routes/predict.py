from flask import Blueprint, request, jsonify
from ..utils.data_loader import get_dataframe
from ..ml.predictor import predict_future_price
from ..live_provider import is_configured, search_live

predict_bp = Blueprint("predict", __name__)


@predict_bp.route("/predict")
def predict():
    name = request.args.get("name", "").strip()
    days = request.args.get("days", type=int, default=30)
    days = max(7, min(days, 90))
    current_price = request.args.get("current_price", type=float)
    if current_price is not None and current_price <= 0:
        current_price = None

    if not name:
        return jsonify({"error": "Product name required"}), 400

    df = get_dataframe()

    # If the caller does not supply a live price (for example from the
    # product-detail page), try to recover the current real listing price
    # before forecasting. Never substitute a fabricated or zero price.
    if current_price is None and is_configured():
        try:
            live_payload = search_live(name, limit=40)
            live_rows = live_payload.get("results", [])
            if live_rows:
                # Prefer the title with the strongest token overlap; exact
                # title matches win naturally.
                import re
                wanted = set(re.findall(r"[a-z0-9]+", name.lower()))
                def match_score(row):
                    title = set(re.findall(r"[a-z0-9]+", str(row.get("product_name", "")).lower()))
                    overlap = len(wanted & title)
                    return (overlap, -abs(len(title) - len(wanted)))
                best = max(live_rows, key=match_score)
                if float(best.get("price") or 0) > 0:
                    current_price = float(best["price"])
        except Exception:
            pass

    result = predict_future_price(name, df, days, current_price=current_price)
    result["product_name"] = name
    return jsonify(result)
