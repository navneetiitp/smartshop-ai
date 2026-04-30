# from flask import Flask, render_template
# from flask_cors import CORS
# from routes.search import search_bp
# from routes.compare import compare_bp
# from routes.predict import predict_bp
# from routes.summary import summary_bp

# app = Flask(
#     __name__,
#     template_folder="../frontend/templates",
#     static_folder="../frontend/static"
# )
# CORS(app)

# app.register_blueprint(search_bp, url_prefix="/api")
# app.register_blueprint(compare_bp, url_prefix="/api")
# app.register_blueprint(predict_bp, url_prefix="/api")
# app.register_blueprint(summary_bp, url_prefix="/api")

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/product/<int:product_id>")
# def product_detail(product_id):
#     return render_template("product.html", product_id=product_id)

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)



from flask import Flask, render_template
from flask_cors import CORS

from backend.routes.search import search_bp
from backend.routes.compare import compare_bp
from backend.routes.predict import predict_bp
from backend.routes.summary import summary_bp

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)

CORS(app)

# Register APIs
app.register_blueprint(search_bp, url_prefix="/api")
app.register_blueprint(compare_bp, url_prefix="/api")
app.register_blueprint(predict_bp, url_prefix="/api")
app.register_blueprint(summary_bp, url_prefix="/api")

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    return render_template("product.html", product_id=product_id)

# Run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)