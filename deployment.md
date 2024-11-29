# Local Development & Deployment Workflow

## Initial Setup

### 1. Branch Setup
```bash
# Ensure you're up to date
git fetch origin
git checkout dev
git pull

# Create feature branch
git checkout -b feature/your-feature
```

### 2. Configure Test Environment
```bash
# Start test environment
docker compose -f docker-compose.test.yaml up -d
# Verify test environment
curl http://localhost:3002  # Should return UI
curl http://localhost:11436 # Should return Ollama API
```

### 3. Configure Production Environment
```bash
# Start production environment
docker compose -f docker-compose.prod.yaml up -d
# Verify production endpoints
curl http://localhost:80     # Should return UI
curl http://localhost:11435  # Should return Ollama API
```

## Development Process

### 1. Frontend Changes
```bash
# Start dev environment
docker compose -f docker-compose.dev.yaml up -d
# Make your changes
# Run frontend tests
npm run test
# Commit and push
git commit -am "feat: your changes"
git push -u origin feature/your-feature
```

### 2. Backend Changes
```bash
# Start dev environment
docker compose -f docker-compose.dev.yaml up -d
# Make your changes
# Run backend tests
pytest backend/tests/
# Commit and push
git commit -am "feat: your changes"
git push -u origin feature/your-feature
```

## Testing Workflow

### 1. Create Pull Request to Dev
- Create PR from your feature branch to dev
- Automated checks will run:
  - Frontend/Backend unit tests
  - Integration tests
  - Code formatting

### 2. Merge to Test Branch
```bash
# After PR approval, merge to test
git checkout test
git merge dev
git push origin test

# Deploy to test environment
docker compose -f docker-compose.test.yaml up -d
```

### 3. End-to-End Testing
```bash
# Run E2E tests in test environment
npm run cypress
# Verify all services
curl http://localhost:3002  # UI
curl http://localhost:11436 # Ollama
```

## Production Deployment

### 1. Manual Approval Process
- Review test results
- Get approval from team lead
- Ensure all tests passed

### 2. Deploy to Production
```bash
# Merge to main after approval
git checkout main
git merge test
git push origin main

# Rebuild and deploy production
docker compose -f docker-compose.prod.yaml up -d --build

# Verify deployment
curl http://localhost:80     # UI
curl http://localhost:11435  # Ollama
curl http://localhost:8000   # ChromaDB
curl http://localhost:8081   # SearXNG
```

## Quick Reference

### Environment Ports
- Dev: UI:3000, Ollama:11434
- Test: UI:3002, Ollama:11436
- Prod: UI:80, Ollama:11435, ChromaDB:8000, SearXNG:8081

### Common Issues
- If tests fail: Check logs with `docker compose -f docker-compose.test.yaml logs`
- If build fails: `docker compose -f docker-compose.prod.yaml build --no-cache`
- Reset environment: `docker compose -f docker-compose.prod.yaml down -v`
