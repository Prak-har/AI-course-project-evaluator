# AI Course Project Evaluator

Full-stack web application for evaluating student project submissions with FastAPI, React, PostgreSQL, FAISS, and the Gemini API through Google's OpenAI-compatible endpoint.

## Stack

- Backend: FastAPI + SQLAlchemy
- Frontend: React + Tailwind CSS + Vite
- Database: PostgreSQL
- Vector Store: FAISS
- LLM: Gemini API via the OpenAI-compatible chat + embeddings endpoint

## Features

- Student login and teacher login
- PDF or text project upload
- Retrieval-augmented evaluation pipeline
- Multi-step scoring and structured feedback
- Draft score before final grading
- Teacher dashboard with rankings and reports
- Relative grading with z-score normalization
- Similarity-based plagiarism checks
- PDF report download

## Project Structure

```text
backend/
  main.py
  routes/
  services/
  rag_pipeline.py
  database.py
frontend/
  src/
    components/
    pages/
```



## Important Note

Uploads work without an LLM key, but evaluation, embeddings, and final grading will not run until you set `LLM_API_KEY` in `.env` and restart the backend. This project is configured by default for Gemini with:

- `LLM_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/`
- `LLM_CHAT_MODEL=gemini-2.5-flash`
- `LLM_EMBEDDING_MODEL=gemini-embedding-001`

## Demo Credentials

- Teacher: `teacher@example.com`
- Password: `teach123`

Students can log in with any email. Demo students are seeded automatically on backend startup.

## API Endpoints

- `POST /auth/login`
- `POST /upload`
- `POST /evaluate`
- `GET /student/{id}`
- `GET /teacher/dashboard`
- `POST /finalize`
- `GET /teacher/report/{submission_id}`
- `GET /health`

## Evaluation Workflow

1. Upload PDF or text and extract project content with PyMuPDF for PDFs.
2. Clean and chunk content.
3. Embed chunks using the Gemini embedding model through the OpenAI-compatible endpoint.
4. Store raw content in PostgreSQL and vectors in FAISS.
5. Retrieve top-k chunks for evaluation.
6. Run feature extraction, scoring, and feedback prompts.
7. Compute weighted total score and persist the evaluation.
8. Finalize relative grading after the deadline.
