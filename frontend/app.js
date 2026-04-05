const express = require('express');
const path = require('path');
const axios = require('axios');
const multer = require('multer');
const FormData = require('form-data');

const app = express();
const port = 3010;

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';
const API_KEY = process.env.API_KEY || 'my-secret-key';

// ── Setup ──────────────────────────────────────────────────────────────────────
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const upload = multer({ storage: multer.memoryStorage() });

// ── Pages ──────────────────────────────────────────────────────────────────────
app.get('/', (req, res) => res.render('index'));

// ── Streaming chat proxy ───────────────────────────────────────────────────────
app.post('/stream', async (req, res) => {
  const { content, session_id } = req.body;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  try {
    const flaskRes = await axios({
      method: 'post',
      url: `${BACKEND_URL}/chat/stream`,
      data: { content, session_id },
      headers: { 'x-api-key': API_KEY, 'Content-Type': 'application/json' },
      responseType: 'stream',
    });
    flaskRes.data.pipe(res);
    flaskRes.data.on('end', () => res.end());
  } catch (err) {
    res.write(`data: ${JSON.stringify({ error: 'Stream failed' })}\n\n`);
    res.end();
  }
});

// ── Chat (non-streaming fallback) ──────────────────────────────────────────────
app.post('/chat', async (req, res) => {
  const { content } = req.body;
  try {
    const response = await axios.post(
      `${BACKEND_URL}/chat`,
      { content },
      { headers: { 'x-api-key': API_KEY } }
    );
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: 'Error contacting backend' });
  }
});

// ── Image generation ───────────────────────────────────────────────────────────
app.post('/generateImage', async (req, res) => {
  const { content } = req.body;
  try {
    const response = await axios.post(
      `${BACKEND_URL}/generateImage`,
      { content },
      { headers: { 'x-api-key': API_KEY, 'response-type': 'base64' } }
    );
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ error: 'Error generating image' });
  }
});

// ── RAG: text upload ───────────────────────────────────────────────────────────
app.post('/upload_docs', async (req, res) => {
  const { texts } = req.body;
  try {
    const response = await axios.post(
      `${BACKEND_URL}/upload_docs`,
      { texts },
      { headers: { 'x-api-key': API_KEY } }
    );
    res.json(response.data);
  } catch (err) {
    res.status(err.response?.status || 500).json(err.response?.data || { error: 'Upload failed' });
  }
});

// ── RAG: PDF upload ────────────────────────────────────────────────────────────
app.post('/upload_pdf', upload.single('file'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });

  const form = new FormData();
  form.append('file', req.file.buffer, {
    filename: req.file.originalname,
    contentType: req.file.mimetype,
  });

  try {
    const response = await axios.post(`${BACKEND_URL}/upload_pdf`, form, {
      headers: { ...form.getHeaders(), 'x-api-key': API_KEY },
    });
    res.json(response.data);
  } catch (err) {
    res.status(err.response?.status || 500).json(err.response?.data || { error: 'PDF upload failed' });
  }
});

// ── RAG: ask ───────────────────────────────────────────────────────────────────
app.post('/ask_rag', async (req, res) => {
  const { query } = req.body;
  try {
    const response = await axios.post(
      `${BACKEND_URL}/ask_rag`,
      { query },
      { headers: { 'x-api-key': API_KEY } }
    );
    res.json(response.data);
  } catch (err) {
    res.status(err.response?.status || 500).json(err.response?.data || { error: 'RAG query failed' });
  }
});

// ── Conversation management ────────────────────────────────────────────────────
app.get('/conversations', async (req, res) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/conversations`, {
      headers: { 'x-api-key': API_KEY },
    });
    res.json(response.data);
  } catch (_) {
    res.json([]);
  }
});

app.get('/conversations/:id/history', async (req, res) => {
  try {
    const response = await axios.get(
      `${BACKEND_URL}/conversations/${req.params.id}`,
      { headers: { 'x-api-key': API_KEY } }
    );
    res.json(response.data);
  } catch (_) {
    res.json({ messages: [] });
  }
});

app.delete('/conversations/:id', async (req, res) => {
  try {
    const response = await axios.delete(
      `${BACKEND_URL}/conversations/${req.params.id}`,
      { headers: { 'x-api-key': API_KEY } }
    );
    res.json(response.data);
  } catch (_) {
    res.status(500).json({ error: 'Delete failed' });
  }
});

// ── Start ──────────────────────────────────────────────────────────────────────
app.listen(port, () => console.log(`Frontend running at http://localhost:${port}`));
