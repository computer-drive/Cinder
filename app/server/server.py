from flask import Flask
from app.logging import get_logger

app = Flask(__name__)

@app.route("/")
def index():
    logger = get_logger("Server")

    logger.info("收到请求")
    return "Hello, World!"