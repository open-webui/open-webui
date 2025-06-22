# Task Completion Workflow

## When a Development Task is Completed

### 1. Code Quality Checks

```bash
# Format code
npm run format          # Frontend formatting
npm run format:backend  # Backend formatting (Black)

# Lint code
npm run lint           # Full linting (frontend + backend)
pylint backend/        # Backend specific linting

# Type checking
npm run check          # TypeScript type checking
```

### 2. Testing

```bash
# Run unit tests
npm run test:frontend  # Frontend tests with Vitest
pytest backend/        # Backend tests with Pytest

# Run integration tests (if applicable)
npm run cy:open        # Cypress e2e tests
```

### 3. Build Verification

```bash
# Test production build
npm run build          # Build frontend
npm run preview        # Preview production build

# Test backend startup
cd backend && python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

### 4. Database Migrations (if schema changed)

```bash
# Generate migration if database models were modified
cd backend && alembic revision --autogenerate -m "description of changes"

# Apply migrations
cd backend && alembic upgrade head
```

### 5. Documentation Updates

- Update README.md if new features added
- Update API documentation if endpoints changed
- Update configuration documentation if new env vars added
- Update CHANGELOG.md following semantic versioning

### 6. Git Workflow

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve bug description"
# or
git commit -m "docs: update documentation"

# Push changes
git push origin feature-branch
```

### 7. System Verification Commands (macOS)

```bash
# Check system resources
ps aux | grep open-webui  # Check if processes are running
lsof -i :8080             # Check if port is in use
df -h                     # Check disk space
free -m                   # Check memory usage (if available)

# Docker verification (if using Docker)
docker ps                 # Check running containers
docker logs open-webui    # Check container logs
```

### 8. Performance Verification

- Check application startup time
- Verify API response times
- Test memory usage under load
- Verify frontend bundle sizes are reasonable

### 9. Pre-deployment Checklist

- [ ] All tests passing
- [ ] Code properly formatted and linted
- [ ] Documentation updated
- [ ] Environment variables documented
- [ ] Database migrations tested
- [ ] No secrets in code
- [ ] Performance is acceptable
- [ ] Security considerations addressed
