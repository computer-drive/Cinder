import traceback

from flask import Flask, jsonify

from app.routes import blueprints
from ..logging import get_logger
app = Flask(__name__)


for blueprint in blueprints:
    app.register_blueprint(blueprint)

@app.errorhandler(Exception)
def handle_exception(e: Exception):
    logger = get_logger("Exception")

    logger.error(f"未捕获的异常：{type(e).__name__} {e}")
    logger.exception(e, exc_info=(type(e), e, e.__traceback__))

    return jsonify({"error": str(e),
        "traceback": traceback.format_exception(type(e), e, e.__traceback__)
    }), 500
