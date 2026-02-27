# Doc Shelf

Doc Shelf is a generic PDF bookshelf app based on `paper-shelf`.

It is focused on organizing and reading any PDF files:
- no paper recommendation/discovery features
- no related-paper or daily-feed features
- simple upload, shelf organization, browsing, and search

## Implementation Note

This project was implemented with **GPT-5.3-Codex** (Codex coding agent workflow).

## Reference Project

- Local reference directory used during implementation: `../paper-shelf`
- Source repository: [cohsh/paper-shelf](https://github.com/cohsh/paper-shelf)

## Features

- Multi-file PDF upload
- Shelf management (create / rename / delete / assign)
- Search by title, author, subject, tags, and full extracted text
- Inline PDF viewer
- Extracted text viewer
- CLI support for add/list/search/show/shelf management

## Project Structure

```text
doc-shelf/
├── src/
│   ├── main.py                 # CLI entry point
│   ├── pdf_extractor.py        # PDF text extraction (PyMuPDF)
│   ├── storage.py              # JSON / Markdown / Text / PDF storage
│   ├── library.py              # Index and shelf management
│   └── server/
│       ├── app.py              # FastAPI app
│       ├── routes_documents.py # Document API
│       ├── routes_shelves.py   # Shelf API
│       ├── routes_upload.py    # Upload + task API
│       └── tasks.py            # Background ingest pipeline
└── web/                        # React + TypeScript + Vite
```

## Setup

### 1. Python

```bash
pip install -e ".[dev]"
```

### 2. Frontend

```bash
cd web
npm install
npm run build
cd ..
```

`npm run build` outputs the frontend bundle to `src/server/static`.

## Run

### Web UI

```bash
doc-shelf serve
# http://127.0.0.1:8000
```

If port `8000` is already in use:

```bash
doc-shelf serve --port 8001
```

### Development mode

```bash
# Backend
doc-shelf serve --dev

# Frontend (another terminal)
cd web
npm run dev
```

## CLI Examples

```bash
# Add a PDF
doc-shelf add ./sample.pdf

# Add to shelves
doc-shelf add ./sample.pdf --shelf reports --shelf personal

# List documents
doc-shelf list

# Search (including extracted text)
doc-shelf search "meeting" --field all

# List shelves
doc-shelf shelf list
```

## Storage Layout

By default, data is stored under `library/`:

- `library/json/`: structured document metadata
- `library/markdown/`: human-readable preview markdown
- `library/texts/`: full extracted text
- `library/pdfs/`: archived source PDFs
- `library/index.json`: library/shelf index

## License

MIT. See [LICENSE](./LICENSE).
