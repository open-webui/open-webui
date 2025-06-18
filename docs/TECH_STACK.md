## Frontend

- **Framework:** SvelteKit
- **Language:** TypeScript
- **Build Tool:** Vite
- **Styling:**
    - Tailwind CSS
- **UI Libraries & Components:**
    - `bits-ui`: Headless UI components.
    - `paneforge`: Draggable and resizable panes.
    - `svelte-sonner`: Toast notifications.
    - `tippy.js`: Tooltips.
    - `@xyflow/svelte`: For creating interactive node-based graphs and diagrams.
    - `codemirror`: Code editor component.
    - `@tiptap/core` (and related extensions): Rich text editor.
    - `marked`: Markdown parser.
    - `mermaid`: For generating diagrams and flowcharts from text in Markdown.
- **Internationalization (i18n):**
    - `i18next` (with `i18next-browser-languagedetector`, `i18next-resources-to-backend`)
- **In-browser Python:**
    - Pyodide (`@pyscript/core`, `pyodide`): Allows running Python code directly in the browser.
- **State Management:**
    - Svelte Stores (native Svelte reactivity system).
- **Testing:**
    - Vitest: Unit and component testing.
    - Cypress: End-to-end testing.

## Backend

- **Framework:** FastAPI (Python)
- **Language:** Python
- **Database:**
    - **ORM/Migration:** SQLAlchemy, Alembic. (Peewee is also present in dependencies, potentially for specific use cases or legacy parts).
    - **Supported Systems:** Likely PostgreSQL (due to `psycopg2-binary` and `pgvector`) and MySQL (due to `PyMySQL`). The specific database is configured via `DATABASE_URL`.
    - **Vector Support:** `pgvector` for PostgreSQL.
- **Caching:** Redis
- **AI/ML Libraries:**
    - **LLM Interaction:** `openai`, `anthropic`, `google-genai`, `langchain`
    - **Embeddings & Vector Stores:**
        - `sentence-transformers`
        - `chromadb`
        - `pymilvus`
        - `qdrant-client`
        - `opensearch-py`
        - `elasticsearch`
        - `pinecone`
    - **Core ML/DL:** `transformers`, `accelerate`
    - **Speech-to-Text (STT):** `faster-whisper`. Also supports STT via external services like OpenAI and Azure.
    - **Text-to-Speech (TTS):** Supports TTS via external services like OpenAI and Azure.
    - **Document Processing:** `pypdf`, `python-pptx`, `docx2txt`, `unstructured`, `nltk`, `Markdown`, `pymdown-extensions`, `pandas`, `openpyxl`, `pyxlsb`, `xlrd` (for various document formats). `pillow`, `opencv-python-headless`, `rapidocr-onnxruntime` for image processing within documents.
- **Authentication:**
    - JWT (JSON Web Tokens) using `python-jose` and `passlib[bcrypt]`.
    - OAuth support using `authlib` for providers like Google, Microsoft, GitHub, and generic OIDC.
    - LDAP integration using `ldap3`.
- **Task Scheduling:** APScheduler
- **File Storage:**
    - Local file system.
    - Cloud Storage: Amazon S3 (via `boto3`), Google Cloud Storage (via `google-cloud-storage`), Azure Blob Storage (via `azure-storage-blob`).
- **Code Execution & Interpretation:**
    - `RestrictedPython`: For sandboxed execution of Python code.
    - Jupyter Integration: Can connect to a Jupyter kernel for more advanced code execution tasks (configured via `CODE_EXECUTION_JUPYTER_URL`).
- **WebSockets:** `python-socketio` for real-time communication.
- **Data Validation:** `pydantic`.

## Other Tools and Practices

- **Containerization:**
    - Docker
    - Docker Compose
- **CI/CD (Continuous Integration/Continuous Deployment):**
    - GitHub Actions: Workflows for building, testing, linting, and deployment are defined in `.github/workflows/`.
- **Testing:**
    - **Backend:** Pytest (implied by `pytest` in `requirements.txt` and common Python practice).
    - **Frontend E2E:** Cypress
    - **Frontend Unit/Component:** Vitest
- **Linters & Formatters:**
    - **Frontend:** ESLint (linting), Prettier (formatting)
    - **Backend:** Pylint (linting), Black (formatting)
- **Build System/Task Runner (General):**
    - `Makefile` is present, suggesting `make` can be used for various development and build tasks.
