from flask import Flask
from app.routes import blueprints

app = Flask(__name__)


for blueprint in blueprints:
    app.register_blueprint(blueprint)
