from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from app.routes import api_blueprint
from app.config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(api_blueprint)

    with app.app_context():
        from app.db import init_db
        init_db()

    return app
