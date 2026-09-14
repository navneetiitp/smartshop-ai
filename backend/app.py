from pathlib import Path
import os

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

# Always load the project-root .env, regardless of the directory used to
# launch Flask. This avoids cwd-dependent configuration bugs.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

from .live_provider import is_configured
from .routes.search import search_bp
from .routes.compare import compare_bp
from .routes.predict import predict_bp
from .routes.summary import summary_bp
from .utils.data_loader import get_dataframe
from .utils.live_history import stats as history_stats

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static",
)

app.register_blueprint(search_bp, url_prefix="/api")
app.register_blueprint(compare_bp, url_prefix="/api")
app.register_blueprint(predict_bp, url_prefix="/api")
app.register_blueprint(summary_bp, url_prefix="/api")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    return render_template("product.html", product_id=product_id)


@app.route("/api/meta")
def meta():
    df = get_dataframe()
    latest = df["date"].max() if not df.empty else None
    stores = sorted(df["website"].dropna().astype(str).unique().tolist()) if not df.empty else []
    return jsonify({
        "live_configured": is_configured(),
        "data_mode": "live_configured" if is_configured() else "historical",
        "historical_rows": int(len(df)),
        "historical_stores": stores,
        "historical_latest": latest.isoformat() if latest is not None and hasattr(latest, "isoformat") else None,
        "live_history": history_stats(),
        "message": (
            "Live shopping provider is configured. A live search is attempted when you search; if the provider fails, the UI falls back to historical data."
            if is_configured()
            else "Using bundled historical data. Configure SERPAPI_KEY to enable live shopping prices."
        ),
    })


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "provider_configured": is_configured(), "data_mode": "live_configured" if is_configured() else "historical"})


@app.errorhandler(500)
def internal_error(error):
    # Keep API failures JSON-shaped so the frontend can show a useful error
    # instead of trying to parse Flask's HTML error page. Do not expose
    # internal tracebacks or environment variables to clients.
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error"}), 500
    return "Internal server error", 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug, port=5000)
