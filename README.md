# Social App - DevSecOps Project

## Project Overview

A modern social web application built with React, FastAPI, and DevSecOps practices. This project focuses on continuous integration, automated testing, and secure deployment.

## 🛠️ Containerised Development Environment

This project is built using **Visual Studio Code Dev Containers**. This ensures that everyone working on the project uses the exact same OS, tools, and dependencies (Python, Node.js, Playwright browsers, etc.) without needing to install them manually on their local machine.

### Prerequisites

Before you begin, ensure you have the following installed:

1.  **Container Runtime** If you are devleoping on a Linux machine, you probably already have Docker installed. Otherwise, choose one of the following options:
    * [**Docker Desktop**](https://www.docker.com/products/docker-desktop/)
    * [**Rancher Desktop**](https://rancherdesktop.io/) (Ensure `dockerd` (moby) is selected in Kubernetes Settings if using this)
    * [**Other alternatives**](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
2.  [**Visual Studio Code**](https://code.visualstudio.com/)
3.  **Dev Containers Extension** for VS Code (id: `ms-vscode-remote.remote-containers`)

## 🚀 Quick Start: Dev Container

This project is designed to run in a VS Code Dev Container. This ensures you have Python, Node.js, Postgres, and all tools (including VS Code extensions) pre-installed.

1. Open Docker Desktop (or Rancher Desktop)
2. Open the project root in VS Code.
3. When prompted, click "Reopen in Container". 
4. Wait for the build to finish. The environment will automatically run make install to set up dependencies.

## Project Structure

```
/
backend/
|
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── auth.py         # Autentisering
│   │           ├── circles.py      # Circle CRUD
│   │           ├── circle_members.py
│   │           ├── posts.py        # Inlägg CRUD
│   │           └── users.py        # Användarsökning
│   │  
│   ├── core/
│   │   ├── config.py              # Konfiguration
│   │   ├── security.py            # JWT, hashing
│   │   └── db.py                  # DB connection
│   │  
│   ├── db/
│   │   ├── models.py              # SQLAlchemy models
│   │   └── database.py            # Session management
│   ├── schemas/
│   │   ├── auth.py                # Pydantic schemas
│   │   └── social.py
│   └── main.py                    # FastAPI app
│   
├── tests/
│   ├── unit/                      # Enhetstester
│   ├── integration/               # Integrationstester
│   ├── e2e/                       # End-to-end tester
│   │   └── step_defs/              
│   │       ├── test_user_dashboard.py  
│   │       ├── test_login.py
│   │       ├── test_registration.py
│   │       └── test_ui.py
│   └── conftest.py                # Shared fixtures (Database, etc.)
│   
├── alembic/                       # Databasmigrationer
|
├── pyproject.toml                 # Dependencies
├── uv.lock
│
docs                               # General project documentation and guides
├── features/                      # BDD Gherkin files
│   ├── login.feature   
|   └── etc...
├── BDD_CONFIGURATION.md
├── etc...
|    
frontend/
|
├── src/
│   ├── components/         # Återanvändbara komponenter
│   ├── pages/              # Sidor (LoginPage, RegisterPage, etc.)
│   ├── services/           # API-kommunikation
│   │   └── auth.service.js
│   ├── hooks/              # Custom React hooks
│   ├── context/            # React Context för state
│   ├── utils/              # Hjälpfunktioner
│   └── App.jsx             # Huvudkomponent
├── public/                 # Statiska filer
├── index.html
├── package.json            # Dependencies
├── vite.config.js          # Build-konfiguration
│
├── Makefile 
└── README.md                     # This file
```


## Standardizing Execution with Makefile

- Single Source of Truth: We use a Makefile to define all our complex build, test, and run commands.
- Local Parity: The exact same commands we type on our laptops (like make test-backend) are the ones GitHub Actions uses.
- Abstracted Complexity: Developers don't need to memorize long Pytest arguments or Playwright flags; the Makefile handles it.

### Select Make commands

Note that these commands should all be run from the root folder of the project.

``` bash
# Show all Make commands
make help

# Install backend and fronted dependencies
make install

# Start development server backend (FastAPI)
# API docs available here: API Docs: http://localhost:8000/docs
make run-backend

# Start development server frontend (requires backend to be running also)
# access at http://localhost:3000
make run-backend
make run-frontend

# Run end-2-end tests
make run-test-backend
make run-frontend
make test-e2e

```


## Frontend Tech Stack

- **React 19** with Vite
- **React Router DOM** v6
- **Axios** for HTTP requests
- **Vitest** + Testing Library (unit/integration)

## Backend Technology Stack

- **Dependency Manager:** uv (replaces pip/poetry)
- **Framework:** FastAPI 
- **Server:** Uvicorn
- **Authentication:** PyJWT (Modern replacement for python-jose)
- **Password Hashing:** pwdlib + argon2 (Modern replacement for passlib)
- **Validation:** Pydantic 
- **Database:** SQLAlchemy, PostgreSQL, Alembic for migrations
- **Testing:** pytest
- **Code Quality:** Ruff (replaces black/flake8/isort) + mypy
- **Security:** bandit


## 🎯 Example Development Workflow using GitHub Flow

1. **Create feature branch** from main
2. **Implement feature** with tests, run tests
3. **Check code quality:** e.g. make lint-backend
4. **Security scan:** e.g. make security-backend
5. **Commit and push** to feature branch
6. **Create Pull Request** (CI will run automatically)
7. **Code review** by team
8. **Merge** to main


## 🧪 Testing Architecture

Our project utilizes a comprehensive, multi-layered testing strategy to ensure reliability across the entire stack. We divide our tests into specific domains to maximize execution speed and maintain clean database states.

### 🐍 Backend Testing (Pytest)
Our backend testing suite focuses on the FastAPI server and database logic, emphasizing speed and transaction safety.
* **Unit Testing:** Tests individual functions, utilities, and isolated business logic. We mock external dependencies and avoid database interactions to provide immediate developer feedback.
* **Integration Testing:** Tests API endpoints, database queries, and SQLAlchemy models natively using `@pytest.mark.asyncio`.
  * **Data Strategy:** We use a highly optimized `db_session` fixture. Instead of wiping the database, this fixture wraps every test in a safe transaction and strictly rolls it back when the test completes. 
* **Execution:** Run via `make test-backend`.

### ⚛️ Frontend Testing (Vitest & React Testing Library)
Our frontend unit and component tests are powered by **Vitest**, chosen for its blazing-fast execution and native integration with our Vite build pipeline.
* **Component Testing:** We use `@testing-library/react` to render components in isolation. We focus on testing how a user interacts with the UI (e.g., finding elements by accessible roles) rather than testing internal React state.
* **DOM Assertions:** Extended with `@testing-library/jest-dom` for highly readable matchers like `toBeInTheDocument()`.
* **Browser Simulation:** We use `jsdom` to simulate a browser environment inside Node.js, allowing us to test clicks and renders in milliseconds without launching a real browser.
* **Structure:** Tests are located in `frontend/src/tests/` or colocated directly next to the components they test (e.g., `Button.test.jsx`).
* **Execution:** Run via `make test-frontend-unit` (or `npm run test:watch` for active development).

### 🎭 End-to-End (E2E) Testing (Playwright & Pytest-BDD)
Our E2E layer tests the complete user journey from the React UI down to the database. It is driven by readable Gherkin `.feature` files and executed via Playwright.
* **Full-Stack Execution:** These are synchronous browser tests that require the FastAPI server, frontend dev server, and test database to be running simultaneously.
* **Database "Nuke" Strategy:** Because the live background server cannot read uncommitted Pytest transactions, we use an `autouse=True` fixture called `clean_database_before_test`. This runs a `TRUNCATE TABLE ... CASCADE` command to completely wipe all data before every single E2E test to prevent state leakage.
* **Synchronous Factories:** We use dedicated synchronous fixtures (like `create_test_user_synchronous`) to physically commit test data to the database before Playwright navigates to the page.
* **Automated XFAILs (BDD):** Gherkin scenarios tagged with `@todo` are automatically mapped to Pytest's `@xfail` marker via a custom hook. This keeps the CI pipeline green while documenting UI features that are waiting on backend implementation.
* **Execution:** Run via `make test-e2e`.


## CI/CD Pipeline

GitHub Actions workflow located in .github/workflows/ci-cd.yml:

Runs on push to main/develop branches and pull requests

#### Common Setup Steps (Run for both jobs)

-    Checkout code: Fetches the repository code so the runner can access it.

-    Initialize CodeQL: Prepares the GitHub Advanced Security scanner for either Python or JavaScript/TypeScript depending on the matrix target.

-    Install uv: Sets up the Python package manager and caches dependencies based on the backend/uv.lock file.

-    Setup Backend Environment: Creates a .env file with database credentials populated from GitHub Secrets and installs backend dependencies.

-    Setup Test Database & Start Server: Seeds the shared PostgreSQL database and boots up the backend server in the background.

#### Backend Job Steps (Python)

-    Lint, Format, Security: Runs static analysis and basic security checks on the Python code.

-    Run Tests: Executes the backend unit and integration tests.

#### Frontend Job Steps (Node.js)

-    Setup Node.js: Initializes Node version 20 and caches npm packages.

-    Install & Audit: Installs frontend dependencies, runs a security audit, and performs linting checks.

-    Unit Tests: Executes the frontend unit tests via Vitest.

-    Playwright Setup: Caches browser binaries using the uv.lock key, and intelligently downloads either the full browsers or just the system dependencies based on whether the cache was hit.

-    Run E2E Tests: Starts the frontend React server, waits for port 3000 to become available, and executes the Playwright end-to-end suite.

#### Teardown & Security Analysis

-    Cleanup: An "always-run" step that safely kills any lingering background npm, node, and uvicorn processes to free up the runner.

-    CodeQL Analysis: Finalizes the security scan and guarantees the results are uploaded to the GitHub Security tab, regardless of whether tests passed or failed.

## Clone the repository

git clone <https://github.com/DiscSecOps/DiscSecOps>


## Important Links

### Frontend App

- http://localhost:3000

### API documentation

- http://localhost:8000/docs

- http://localhost:8000/redoc

### VNC session for viewing headed Playwright tests

- http://localhost:6080

## Notes

- Playwright browsers are pre-installed in the Dev Container

- The project follows DevSecOps principles with security integrated from the start

- Feature development uses slicing methodology for incremental delivery

## Contributors

- Camelia Ciuca
- Haidar Alany
- Mattias Hammarhorn
- Richard Orme
- Shahzad Babar

## License
MIT