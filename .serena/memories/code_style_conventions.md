# Code Style and Conventions

## Python Backend Style

- **Formatter**: Black with default settings
- **Linter**: Pylint
- **Type Hints**: Strongly encouraged, especially for function signatures
- **Docstrings**: Use for public APIs and complex functions
- **Import Organization**: Follow PEP 8 standards
- **Variable Naming**: snake_case for variables and functions, PascalCase for classes
- **Constants**: UPPER_CASE for module-level constants

## Code Quality Standards

- **Line Length**: Black default (88 characters)
- **String Quotes**: Black will standardize (double quotes preferred)
- **Trailing Commas**: Black handles automatically
- **Function Organization**: Keep functions focused and single-purpose
- **Error Handling**: Use proper exception handling with specific exception types

## API Design Patterns

- **FastAPI Routers**: Organize endpoints by domain (users, chats, models, etc.)
- **Pydantic Models**: Use for request/response validation
- **Response Models**: Consistent JSON structure with proper HTTP status codes
- **Authentication**: JWT-based with dependency injection
- **Database Models**: SQLAlchemy ORM with proper relationships

## Frontend Style

- **Framework**: SvelteKit with TypeScript
- **Styling**: Tailwind CSS utility classes
- **Component Organization**: Modular components in `src/lib/`
- **State Management**: Svelte stores for global state
- **Type Safety**: TypeScript throughout the frontend

## Configuration Management

- **Environment Variables**: Extensive use of env vars for configuration
- **Default Values**: Sensible defaults in `config.py`
- **Validation**: Pydantic for configuration validation
- **Documentation**: Document all configuration options

## Database Design

- **Migrations**: Alembic for database schema changes
- **Relationships**: Proper foreign keys and relationships
- **Indexes**: Strategic indexing for performance
- **Naming**: Descriptive table and column names

## Security Practices

- **Authentication**: JWT tokens with proper expiration
- **Authorization**: Role-based access control
- **Input Validation**: Pydantic models for all inputs
- **SQL Injection**: SQLAlchemy ORM prevents direct SQL
- **CORS**: Proper CORS configuration
- **Environment Secrets**: Never commit secrets to version control

## Testing Conventions

- **Backend Tests**: Pytest with fixtures
- **Frontend Tests**: Vitest for unit tests
- **E2E Tests**: Cypress for integration testing
- **Test Organization**: Mirror source code structure
- **Mocking**: Mock external dependencies in tests
