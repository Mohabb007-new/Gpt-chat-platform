# GPT Chat Platform

A full-stack AI chat application built with **Flask** and **Node.js**, featuring real-time streaming responses, persistent conversation history, RAG (Retrieval-Augmented Generation) with PDF ingestion, and image generation — all in a clean, modern chat UI.

---

## Features

- **Streaming Chat** — responses stream token-by-token in real time
- **Persistent Conversations** — chat history stored in SQLite, survives server restarts
- **Conversation Sidebar** — browse, switch between, and delete past conversations
- **RAG** — upload PDFs or plain text, then ask questions grounded in your documents
- **PDF Ingestion** — drag-and-drop PDF upload; pages are automatically indexed in FAISS
- **Image Generation** — generate images from text prompts via OpenAI
- **Session Memory** — multi-turn conversations with rolling context
- **Fake/Test Mode** — runs fully offline with no API key (for development and testing)
- **Dockerized** — one command to run everything

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| AI | OpenAI API (GPT-4o-mini, text-embedding-3-small, gpt-image-1) |
| RAG / Vector search | FAISS (persisted to disk) |
| Conversation storage | SQLite |
| PDF parsing | pypdf |
| Frontend | Node.js, Express, EJS |
| Container | Docker, Docker Compose |
| CI/CD | GitHub Actions |

---

## Quick Start

### With Docker (recommended)

Create a `.env` file in the project root:
```
OPENAI_API_KEY=your-openai-key
API_KEY=your-api-key
```

Then run:
```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend (chat UI) | http://localhost:3010 |
| Backend API | http://localhost:5000 |

### Without Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
cp ../.env .env
flask run --host=0.0.0.0

# Frontend (separate terminal)
cd frontend
npm install
node app.js
```

---

## API Reference

All endpoints (except `/upload_docs`) require:
```
x-api-key: your-api-key
```

### Chat

| Method | Endpoint | Description |
|---|---|---|
| POST | `/chat` | Single-turn chat, returns full response |
| POST | `/chat/stream` | Streaming chat via SSE, saves to conversation history |

**Streaming request body:**
```json
{ "content": "Hello!", "session_id": "user123" }
```

### RAG

| Method | Endpoint | Description |
|---|---|---|
| POST | `/upload_docs` | Upload plain text strings into FAISS |
| POST | `/upload_pdf` | Upload a PDF file (multipart/form-data) |
| POST | `/ask_rag` | Ask a question against indexed documents |
| POST | `/chat_rag_memory` | Multi-turn RAG chat with session memory |

### Image Generation

| Method | Endpoint | Description |
|---|---|---|
| POST | `/generateImage` | Generate an image; set `response-type: base64` or `image` header |

### Conversations

| Method | Endpoint | Description |
|---|---|---|
| GET | `/conversations` | List all conversations (session ID, preview, message count) |
| GET | `/conversations/<id>` | Get full message history for a session |
| DELETE | `/conversations/<id>` | Delete a conversation |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── __init__.py        # App factory, DB init
│   │   ├── routes.py          # All API endpoints
│   │   ├── openai_service.py  # Chat + image + streaming
│   │   ├── rag_service.py     # FAISS, embeddings, PDF ingestion
│   │   ├── memory_service.py  # Session memory (SQLite-backed)
│   │   ├── db.py              # SQLite persistence layer
│   │   └── config.py          # Environment config
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app.js                 # Express server + API proxy
│   ├── views/index.ejs        # Chat UI (streaming, sidebar, all modes)
│   └── public/style.css       # UI styles
├── docker-compose.yml
└── .env                       # (create this, not committed)
```

---

## Running Tests

```bash
cd backend
pytest -v
```

Tests run in fake mode (no real API calls needed).

---

## CI/CD

GitHub Actions pipeline:
- Runs pytest on every push
- Builds and pushes Docker image to Docker Hub

---

## License

MIT
