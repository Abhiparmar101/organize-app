from flask import Flask
from flask_cors import CORS
from .routes import configure_routes,monitor_log_and_trigger_api
from threading import Thread
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_pyfile('config.py')

    configure_routes(app)
    # Start log monitoring in a background thread
    thread = Thread(target=monitor_log_and_trigger_api, daemon=True)
    thread.start()
    return app