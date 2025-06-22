# Development Commands and Scripts

## Essential Commands for Development

### Backend Development

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run backend in development mode
cd backend && python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload

# Run with uv (modern Python package manager)
cd backend && uv run uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Run tests
pytest backend/

# Code formatting
black . --exclude ".venv/|/venv/"

# Linting
pylint backend/
```

### Frontend Development

```bash
# Install dependencies
npm install

# Development server
npm run dev
npm run dev:5050  # Run on port 5050

# Build for production
npm run build

# Build with watch mode
npm run build:watch

# Preview production build
npm run preview

# Type checking
npm run check
npm run check:watch

# Linting
npm run lint:frontend

# Formatting
npm run format

# Prepare Pyodide
npm run pyodide:fetch

# Internationalization
npm run i18n:parse
```

### Full Stack Commands

```bash
# Format both frontend and backend
npm run format && npm run format:backend

# Lint everything
npm run lint  # Runs lint:frontend, lint:types, lint:backend

# Testing
npm run test:frontend
pytest backend/  # Backend tests

# End-to-end testing
npm run cy:open
```

### Docker Development

```bash
# Using Makefile
make install        # docker-compose up -d
make start         # docker-compose start
make stop          # docker-compose stop
make startAndBuild # docker-compose up -d --build
make update        # Update and rebuild

# Direct docker-compose
docker-compose up -d
docker-compose up -d --build
docker-compose logs -f
```

### Database Commands

```bash
# Reset database
rm backend/data/webui.db  # For SQLite

# Run migrations
cd backend && alembic upgrade head

# Create new migration
cd backend && alembic revision --autogenerate -m "migration description"
```
