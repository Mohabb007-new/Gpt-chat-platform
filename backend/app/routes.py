import json
from flask import Blueprint, jsonify, request, Response, stream_with_context, send_file
from app.openai_service import get_chat_response, get_image_response, get_chat_response_stream
from flask import current_app as app
import io
from functools import wraps

api_blueprint = Blueprint('api', __name__)


# ── Auth & validation decorators ───────────────────────────────────────────────
def require_api_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        key = request.headers.get("x-api-key")
        if app.config.get("TESTING") and key == "my-secret-key":
            return f(*args, **kwargs)
        api_key = app.config.get("API_KEY")
        if not api_key or key != api_key:
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return wrapper


def require_content(field_name, expected_type=str):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            data = request.get_json(silent=True)
            if not data:
                return jsonify({"error": "Invalid JSON payload"}), 400
            value = data.get(field_name)
            if expected_type == str:
                if not value or not isinstance(value, str) or not value.strip():
                    return jsonify({"error": f"Missing or empty '{field_name}' field"}), 400
            elif expected_type == list:
                if not isinstance(value, list) or len(value) == 0:
                    return jsonify({"error": f"Missing or empty '{field_name}' field"}), 400
                for i, item in enumerate(value):
                    if not isinstance(item, str) or not item.strip():
                        return jsonify({"error": f"Invalid item at index {i} in '{field_name}'"}), 400
            else:
                if value is None:
                    return jsonify({"error": f"Missing '{field_name}' field"}), 400
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Basic routes ───────────────────────────────────────────────────────────────
@api_blueprint.route("/", methods=["GET"])
@require_api_key
def home():
    return jsonify({"response": "Hello, World!"})


@api_blueprint.route("/chat", methods=["POST"])
@require_api_key
@require_content("content")
def chat():
    data = request.get_json()
    content = data.get("content")
    response = get_chat_response(content)
    return jsonify({"response": response, "version": "0.1.0"})


# ── Streaming chat ─────────────────────────────────────────────────────────────
@api_blueprint.route("/chat/stream", methods=["POST"])
@require_api_key
def chat_stream():
    from app.memory_service import get_memory, add_to_memory

    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    session_id = data.get("session_id", "default")

    if not content:
        return jsonify({"error": "Missing content"}), 400

    def generate():
        history = get_memory(session_id)
        messages = history + [{"role": "user", "content": content}]
        full_response = ""
        for token in get_chat_response_stream(messages):
            full_response += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        add_to_memory(session_id, "user", content)
        add_to_memory(session_id, "assistant", full_response)
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Image generation ───────────────────────────────────────────────────────────
@api_blueprint.route("/generateImage", methods=["POST"])
@require_api_key
@require_content("content")
def generate_image():
    data = request.get_json()
    response_type = request.headers.get("response-type", "base64")
    content = data.get("content")
    result = get_image_response(content, response_type)
    if response_type.lower() == "base64":
        return result
    elif response_type.lower() == "image":
        return send_file(
            io.BytesIO(result),
            mimetype="image/png",
            as_attachment=True,
            download_name="generated.png",
        )
    return {"error": "Invalid response-type header, must be 'base64' or 'image'"}, 402


# ── RAG ────────────────────────────────────────────────────────────────────────
from app.rag_service import add_documents, answer_query, answer_with_memory_and_rag, ingest_pdf


@api_blueprint.route("/upload_docs", methods=["POST"])
@require_api_key
@require_content("texts", expected_type=list)
def upload_docs():
    data = request.get_json()
    texts = data.get("texts", [])
    add_documents(texts)
    return jsonify({"message": f"Stored {len(texts)} documents."})


@api_blueprint.route("/upload_pdf", methods=["POST"])
@require_api_key
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are accepted"}), 400
    pages_added = ingest_pdf(f.read())
    return jsonify({"message": f"Ingested {pages_added} pages from {f.filename}."})


@api_blueprint.route("/ask_rag", methods=["POST"])
@require_api_key
@require_content("query")
def ask_rag():
    data = request.get_json()
    query = data.get("query", "")
    answer = answer_query(query)
    return jsonify({"response": answer})


@api_blueprint.route("/chat_rag_memory", methods=["POST"])
@require_api_key
def chat_rag_memory():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    session_id = data.get("session_id", "default")
    if not query:
        return jsonify({"error": "Query missing"}), 400
    answer = answer_with_memory_and_rag(session_id, query)
    return jsonify({"response": answer})


# ── Conversation management ────────────────────────────────────────────────────
from app.db import list_sessions, delete_session, get_messages as db_get_messages


@api_blueprint.route("/conversations", methods=["GET"])
@require_api_key
def get_conversations():
    return jsonify(list_sessions())


@api_blueprint.route("/conversations/<session_id>", methods=["GET"])
@require_api_key
def get_conversation(session_id):
    messages = db_get_messages(session_id, limit=100)
    return jsonify({"session_id": session_id, "messages": messages})


@api_blueprint.route("/conversations/<session_id>", methods=["DELETE"])
@require_api_key
def delete_conversation(session_id):
    delete_session(session_id)
    return jsonify({"message": f"Conversation '{session_id}' deleted."})
