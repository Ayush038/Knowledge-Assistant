from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from auth.routes import auth_bp
from documents.routes import document_bp
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()
import threading
import time
from embeddings.ingest_chunks import ingest_chunks
import os
from chat.routes import chat_bp
from admin.routes import admin_bp
load_dotenv()
import os


def embedding_worker():
    while True:
        try:
            ingest_chunks()
        except Exception as e:
            print("Embedding worker error:", e)
        time.sleep(10)

def start_embedding_worker():
    thread = threading.Thread(target=embedding_worker, daemon=True)
    thread.start()

def create_app():
    app=Flask(__name__)
    app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    CORS(app)
    JWTManager(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(document_bp,url_prefix="/document")
    app.register_blueprint(chat_bp,url_prefix="/chat")
    app.register_blueprint(admin_bp,url_prefix="/admin")

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_embedding_worker()
    return app

app = create_app()


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)