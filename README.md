# RFP Validation API

FastAPI service for scoring partner responses against RFP requirements and recommending relevant training when the score is below 70%.

## Features

- Select an RFP title and retrieve 10 random requirements.
- Score exactly 10 YES/NO answers (10 points per correct answer).
- If the score is below 70%, identify incorrectly answered requirements and search the local training catalogue semantically.
- Ingest the training Excel workbook into a persistent local Chroma vector database using local Sentence Transformers embeddings.
- Keep the workbook, SQLite database, and vector database out of Git.

## 1. Set up on Windows

Open the repository folder in VS Code. In the terminal, run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation, run this for the current terminal session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2. Add the local Excel workbook

Copy your training catalogue to `data/training.xlsx`. The first row must contain these column names:

- `Series Name`
- `Stage`
- `Architecture`
- `Program Track`
- `Track`
- `Role`
- `Language`
- `Learning Plan Type`
- `ENABLEMENT_BUSINESS_ENTITY`
- `Description`
- `Series URL`

The three core fields `Series Name`, `Description`, and `Series URL` must exist. Other listed fields may be blank, but their headers should be present if available. The script reads the active worksheet in read-only mode and processes rows in batches.

**Do not commit the workbook.** All `.xlsx` files are ignored by Git.

## 3. Create/populate the local Chroma vector store

Run this from the repository root, with the virtual environment active:

```powershell
python -m scripts.ingest_training
```

This command creates the `chroma_db/` directory and a `training_catalogue` collection, downloads the embedding model the first time it is needed, embeds training records in batches, and writes them to disk. It is safe to rerun: existing records are updated, duplicate identities within the workbook are skipped, and records removed from the workbook are deleted after successful ingestion.

Default embedding model: `all-MiniLM-L6-v2`. It runs locally after download and does not require an API key. The initial dependency/model download can take a while.

Optional environment variables:

- `TRAINING_EXCEL_PATH`: workbook path (default `data/training.xlsx`)
- `CHROMA_PERSIST_DIRECTORY`: Chroma path (default `chroma_db/`)
- `TRAINING_EMBEDDING_MODEL`: Sentence Transformers model name (default `all-MiniLM-L6-v2`)
- `TRAINING_MIN_SIMILARITY`: minimum cosine similarity accepted (default `0.20`)
- `TRAINING_INGEST_BATCH_SIZE`: ingestion batch size (default `128`)

The local Chroma directory is ignored by Git. Re-run ingestion whenever the workbook changes.

## 4. Start the API

```powershell
uvicorn app.main:app --reload
```

Open the interactive API documentation at http://127.0.0.1:8000/docs and health check at http://127.0.0.1:8000/health.

## 5. How recommendations work

1. The client retrieves 10 requirements for a selected RFP title.
2. The client submits 10 YES/NO responses to `POST /rfp/score`.
3. The API compares the responses with the expected answers in SQLite.
4. At 70% or above, no training search is run.
5. Below 70%, the API searches Chroma for each failed requirement, de-duplicates courses, ranks them by best semantic similarity, and returns up to five recommendations.

The score response includes `training_recommendation_status`:

- `not_needed`: score is 70% or higher.
- `recommendations_available`: matching training was found.
- `no_relevant_training`: the index was queried but nothing passed the similarity threshold.
- `index_not_ready`: Chroma is empty or the local search/model failed. Scoring still succeeds; run ingestion and check the terminal log.

Each recommendation includes the course name, description, URL, available catalogue metadata, the failed requirement it matched, and a relevance score between 0 and 1. The similarity threshold is a starting point and should be tuned using real examples.

## Example score request

Send exactly 10 unique requirement IDs returned by the requirements endpoint:

```json
{
  "responses": [
    {"id": 1, "response": "YES"},
    {"id": 2, "response": "NO"},
    {"id": 3, "response": "YES"},
    {"id": 4, "response": "YES"},
    {"id": 5, "response": "NO"},
    {"id": 6, "response": "YES"},
    {"id": 7, "response": "NO"},
    {"id": 8, "response": "YES"},
    {"id": 9, "response": "YES"},
    {"id": 10, "response": "NO"}
  ]
}
```

Use IDs from your actual API response; the IDs above are illustrative.
