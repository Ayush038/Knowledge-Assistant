from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from auth.routes import auth_bp
from documents.routes import document_bp
import threading
from embeddings.ingest_chunks import ingest_chunks
import os
from chat.routes import chat_bp
from admin.routes import admin_bp
from config import Config
from extensions import limiter
from logger import get_logger
import time
import atexit

logger = get_logger(__name__)

stop_event = threading.Event()


def embedding_worker():
    logger.info("Embedding worker started")
    while not stop_event.is_set():
        try:
            ingest_chunks()
        except Exception as e:
            logger.error("Embedding worker error", exc_info=e)

        stop_event.wait(10)

def start_embedding_worker():
    thread = threading.Thread(target=embedding_worker, daemon=True)
    thread.start()


def stop_embedding_worker():
    logger.info("Stopping embedding worker")
    stop_event.set()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={r"/*": {"origins": [
            "http://116.202.210.102:3500"
        ]}},
        supports_credentials=True
    )
    JWTManager(app)
    limiter.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(document_bp, url_prefix="/document")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


app = create_app()

if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    start_embedding_worker()

atexit.register(stop_embedding_worker)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)