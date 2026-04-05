import faiss
import numpy as np
import os
import pickle
from openai import OpenAI

# ── Persistence paths ──────────────────────────────────────────────────────────
DATA_DIR = os.getenv("DATA_DIR", "data")
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss.index")
DOCS_PATH = os.path.join(DATA_DIR, "documents.pkl")

embedding_dim = 1536  # text-embedding-3-small


# ── Fake mode ──────────────────────────────────────────────────────────────────
def _is_fake_mode() -> bool:
    if os.getenv("FORCE_FAKE_OPENAI"):
        return True
    if os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from flask import current_app
        if current_app and current_app.config.get("TESTING"):
            return True
    except Exception:
        pass
    return True


# ── OpenAI client ──────────────────────────────────────────────────────────────
_client = None


def _get_client():
    global _client
    if _is_fake_mode():
        return None
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# ── FAISS index with disk persistence ─────────────────────────────────────────
_index = None
_documents = []


def _get_index():
    global _index, _documents
    if _index is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(DOCS_PATH):
            _index = faiss.read_index(FAISS_INDEX_PATH)
            with open(DOCS_PATH, "rb") as f:
                _documents = pickle.load(f)
        else:
            _index = faiss.IndexFlatL2(embedding_dim)
            _documents = []
    return _index, _documents


def _save_index():
    idx, docs = _get_index()
    os.makedirs(DATA_DIR, exist_ok=True)
    faiss.write_index(idx, FAISS_INDEX_PATH)
    with open(DOCS_PATH, "wb") as f:
        pickle.dump(docs, f)


# ── Embedding ──────────────────────────────────────────────────────────────────
def embed_text(texts):
    if _is_fake_mode():
        embeddings = []
        for i, t in enumerate(texts):
            vec = np.full((embedding_dim,), float((i + 1) % 10), dtype=np.float32)
            vec += float(len(t) % 5)
            embeddings.append(vec)
        return embeddings
    client = _get_client()
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [np.array(d.embedding, dtype=np.float32) for d in response.data]


# ── Document management ────────────────────────────────────────────────────────
def add_documents(text_list):
    idx, docs = _get_index()
    embeddings = embed_text(text_list)
    faiss_matrix = np.vstack(embeddings)
    idx.add(faiss_matrix)
    docs.extend(text_list)
    _save_index()


def ingest_pdf(file_bytes: bytes) -> int:
    """Extract text from a PDF and store in FAISS. Returns number of pages added."""
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(file_bytes))
    texts = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            texts.append(text.strip())
    if texts:
        add_documents(texts)
    return len(texts)


def retrieve_context(query, top_k=3):
    idx, docs = _get_index()
    if idx.ntotal == 0:
        return []
    query_emb = embed_text([query])[0].reshape(1, -1)
    distances, indices = idx.search(query_emb, min(top_k, idx.ntotal))
    return [docs[i] for i in indices[0] if i < len(docs)]


# ── Answering ──────────────────────────────────────────────────────────────────
def answer_query(query):
    context = retrieve_context(query)
    if _is_fake_mode():
        return f"(test) Answer to: {query}"
    context_text = "\n\n".join(context) if context else "No context found."
    prompt = f"Use the following context to answer:\n{context_text}\n\nQuestion: {query}"
    client = _get_client()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content


from app.memory_service import add_to_memory, get_memory


def answer_with_memory_and_rag(session_id, user_query):
    context = retrieve_context(user_query)
    context_text = "\n\n".join(context) if context else "No external context found."
    history = get_memory(session_id)
    messages = history + [
        {"role": "system", "content": f"Use the following context:\n{context_text}"},
        {"role": "user", "content": user_query},
    ]
    if _is_fake_mode():
        response = f"(test) Memory+RAG answer to: {user_query}"
    else:
        client = _get_client()
        completion = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages
        )
        response = completion.choices[0].message.content
    add_to_memory(session_id, "user", user_query)
    add_to_memory(session_id, "assistant", response)
    return response
