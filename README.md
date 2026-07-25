# Enterprise AI Data Assistant

Ask questions about your spreadsheets in plain English and get back SQL, results, charts
and written insights. Multiple LLMs generate SQL in parallel; the results are validated,
ranked by consensus, and only the safest, highest-scoring query is executed.

No login — the app is open access on your machine.

---

## Quick start

```bash
# 1. Install backend dependencies
venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. Add at least one LLM API key (see "LLM providers" below)
#    Edit backend/.env

# 3. Build the frontend (once, or after any UI change)
python manage.py build-frontend

# 4. Run
python manage.py runserver
```

Then open **http://localhost:8000** — upload an `.xlsx`, `.xls` or `.csv` file and ask away.

| URL | What |
|---|---|
| http://localhost:8000 | The app |
| http://localhost:8000/docs | Interactive API docs (Swagger) |
| http://localhost:8000/api/health | Health check + configured providers |

### Commands

```bash
python manage.py runserver        # start on port 8000
python manage.py runserver 9000   # custom port
python manage.py build-frontend   # npm install (if needed) + vite build
python manage.py help
```

`runserver` serves both the API and the built React app, so one command runs everything.
For frontend development with hot reload, run `npm run dev` in `frontend/` alongside it
and use http://localhost:5173.

---

## LLM providers

Set any of these in `backend/.env`. Each provider activates only when its key is present,
so leaving one blank simply drops it from the consensus panel. **You need at least one.**

### Free — no card required

| Key | Where to get it | Models used |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com/keys](https://console.groq.com/keys) | Llama 3.3 70B, gpt-oss-120b, Qwen3.6 27B, Llama 3.1 8B |
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) | Gemma 4 31B, north-mini-code, Nemotron 3 Super |
| `GITHUB_MODELS_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) | Llama 3.3 70B, Codestral 2501, Phi-4 |
| `CEREBRAS_API_KEY` | [cloud.cerebras.ai](https://cloud.cerebras.ai) | Llama 3.3 70B |
| `MISTRAL_API_KEY` | [console.mistral.ai](https://console.mistral.ai) | Mistral Small |
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Gemini 2.0 Flash |

**Ollama** needs no key at all — install from [ollama.com](https://ollama.com), run
`ollama serve` and `ollama pull llama3.2`. Fully local and unlimited.

### Paid

`DEEPSEEK_API_KEY` and `OPENAI_API_KEY` both require account credit; DeepSeek has no free tier.

Model ids drift as providers retire models. They live in `GROQ_MODELS` and
`OPENAI_COMPATIBLE_PROVIDERS` in [backend/app/services/llm_service.py](backend/app/services/llm_service.py) —
if a provider starts returning "model not found", update the list there.

Settings are cached, so **restart the server** after editing `.env`. On startup the log
prints which providers were picked up.

---

## How a query works

1. **Schema context** — table and column info is retrieved from the RAG index (`rag_service`)
2. **Prompt** — schema + question are assembled into a SQL-generation prompt (`prompt_service`)
3. **Fan-out** — the prompt goes to every configured model in parallel (`llm_service`)
4. **Validate** — each candidate must be a single read-only `SELECT`, with tables and
   columns that exist; destructive statements are rejected (`validator_service`, `core/security.py`)
5. **Rank** — candidates score on validation, cross-model agreement, latency and complexity;
   the winner's score becomes the confidence percentage (`ranking_service`)
6. **Execute** — the best query runs with a timeout (`executor_service`)
7. **Present** — the LLM then recommends a chart type and writes insights on the results

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/upload/excel` | Upload `.xlsx` / `.xls` / `.csv`, creating a SQL table |
| `GET` | `/api/upload/datasets` | List uploaded datasets |
| `GET` | `/api/upload/datasets/{id}/preview` | Preview rows |
| `DELETE` | `/api/upload/datasets/{id}` | Delete a dataset and its table |
| `POST` | `/api/query` | Ask a natural language question |
| `GET` | `/api/query/history` | Past queries |
| `GET` | `/api/query/tables` | Available tables and columns |
| `GET` | `/api/query/providers` | Registered models and availability |
| `GET` | `/api/admin/stats` | Totals, success rate, average confidence |
| `GET` | `/api/admin/logs` | Query audit log |
| `POST` | `/api/export/download` | Export results as CSV / Excel / PDF |

## Project structure

```
TEXT-SQL-AI/
├── manage.py                  # runserver / build-frontend
├── backend/
│   ├── .env                   # your API keys (gitignored)
│   ├── requirements.txt
│   ├── data/                  # SQLite DBs, uploads, vector store (gitignored)
│   └── app/
│       ├── main.py            # FastAPI app; also serves frontend/dist
│       ├── config.py          # settings + API-key validation
│       ├── database.py        # app DB (metadata) + data DB (your tables)
│       ├── models/            # Dataset, QueryLog, SchemaMetadata
│       ├── routers/           # upload, query, admin, export
│       ├── services/          # excel, rag, prompt, llm, validator, ranking, executor, export
│       ├── core/              # SQL-injection detection, rate limiting, exceptions
│       └── llm_providers/     # gemini, groq, ollama, deepseek, openai-compatible
└── frontend/
    ├── dist/                  # build output served by the backend (gitignored)
    └── src/
        ├── pages/             # Query, Upload, Datasets, History, Dashboard, Admin, Settings
        ├── components/Layout/ # sidebar + shell
        ├── services/api.ts    # axios client
        └── types/             # shared TypeScript interfaces
```

Two SQLite databases are used deliberately: `app.db` holds metadata and audit logs, while
`user_data.db` holds the tables created from your spreadsheets. Generated SQL only ever
touches the second one.

## Notes

- **Read-only by design.** Only `SELECT` passes validation. `DROP`, `DELETE`, `UPDATE`,
  `INSERT`, `ALTER`, multiple statements and comment-based injection are all blocked.
- **Free tiers are rate limited.** Each question costs roughly one call per configured
  model plus two more (chart + insights). A `429` means throttling, not a billing problem.
- **Never commit `backend/.env`.** It is gitignored — keep it that way.
