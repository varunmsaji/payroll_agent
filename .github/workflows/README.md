# GitHub Actions CI Pipeline

This directory contains GitHub Actions workflows for Continuous Integration.

## 🔄 Workflows

### CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main`, `master`, or `develop` branches
- Pull requests to `main`, `master`, or `develop` branches
- Manual workflow dispatch

**Jobs:**

#### 1. Code Quality Checks
- **Black**: Code formatting verification
- **isort**: Import sorting verification
- **Ruff**: Fast Python linting

#### 2. Security Scanning
- **Bandit**: Security vulnerability detection in code
- **Safety**: Dependency vulnerability scanning
- Uploads security reports as artifacts

#### 3. Tests
- Runs pytest with coverage reporting
- Generates HTML, XML, and terminal coverage reports
- Enforces minimum 50% code coverage
- Uploads coverage reports as artifacts

#### 4. Docker Build
- Builds Docker image with layer caching
- Tests the container starts successfully
- **Trivy**: Scans image for vulnerabilities
- Uploads vulnerability scan results

#### 5. Summary
- Aggregates results from all jobs
- Fails if any critical job fails
- Provides clear pass/fail status

---

## 🚀 Running Workflows

### Automatic Triggers
Workflows run automatically on:
- Every push to main/master/develop branches
- Every pull request to main/master/develop branches

### Manual Trigger
1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "CI Pipeline" workflow
4. Click "Run workflow" button
5. Select branch and click "Run workflow"

---

## 📊 Viewing Results

### In Pull Requests
- Check status appears on PR page
- Click "Details" to see full logs
- Review failed checks and error messages

### In Actions Tab
1. Navigate to Actions tab in GitHub
2. Click on a workflow run
3. View job summaries and logs
4. Download artifacts (coverage reports, security scans)

---

## 🔧 Local Testing

Before pushing, run these checks locally:

### Install Development Dependencies
```bash
pip install -r requirements-dev.txt
```

### Code Quality
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint code
ruff check app/
```

### Security Scanning
```bash
# Scan code for security issues
bandit -r app/

# Check dependencies
safety check
```

### Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # On macOS
xdg-open htmlcov/index.html  # On Linux
```

### Test Docker Build
```bash
# Build image
docker build -t payroll-backend:test .

# Run container
docker run -p 7860:7860 payroll-backend:test
```

---

## 🔐 Secrets Configuration

No secrets are required for CI-only pipeline. All checks run without external dependencies.

If you add deployment later, you'll need to configure:
- Navigate to Repository → Settings → Secrets and Variables → Actions
- Click "New repository secret"
- Add required secrets

---

## 🐛 Troubleshooting

### Code Quality Checks Failing

**Black formatting errors:**
```bash
# Fix automatically
black app/
git add .
git commit -m "Fix code formatting"
```

**isort import errors:**
```bash
# Fix automatically
isort app/
git add .
git commit -m "Fix import sorting"
```

**Ruff linting errors:**
```bash
# See specific errors
ruff check app/

# Fix some issues automatically
ruff check app/ --fix
```

### Tests Failing

**Check pytest output:**
```bash
pytest tests/ -v --tb=short
```

**Run specific test:**
```bash
pytest tests/test_api_health.py::test_app_startup -v
```

**Check coverage:**
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Docker Build Failing

**Check build locally:**
```bash
docker build -t test . --progress=plain
```

**Check disk space:**
```bash
docker system df
docker system prune -a  # Clean up if needed
```

**Check memory:**
GitHub Actions runners have limited memory. If build fails due to memory:
- Reduce image size
- Use multi-stage builds (already implemented)
- Optimize dependencies

### Security Scan Warnings

**Bandit warnings:**
- Review code flagged by Bandit
- Add `# nosec` comment if false positive (carefully!)
- Fix actual security issues

**Safety vulnerabilities:**
- Update vulnerable packages in requirements.txt
- Pin to secure versions
- Check for patches or alternatives

---

## 📈 Coverage Reports

Coverage reports are uploaded as artifacts after each test run:

1. Go to Actions → Select workflow run
2. Scroll to "Artifacts" section
3. Download "coverage-reports"
4. Extract and open `htmlcov/index.html`

---

## 🎯 Best Practices

### Before Pushing
1. ✅ Run tests locally
2. ✅ Check code quality (Black, isort, Ruff)
3. ✅ Review security warnings
4. ✅ Ensure tests pass with good coverage

### Pull Request Checklist
1. ✅ All CI checks pass
2. ✅ Code coverage doesn't decrease
3. ✅ No new security vulnerabilities
4. ✅ Code is formatted and linted

### Commit Messages
Use clear, descriptive commit messages:
- ✅ `Add user authentication endpoint`
- ✅ `Fix face recognition confidence calculation`
- ❌ `Update`
- ❌ `Fix bug`

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Ruff Linter](https://docs.astral.sh/ruff/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
