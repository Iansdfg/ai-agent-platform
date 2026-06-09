PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_UVICORN := $(VENV)/bin/uvicorn
APP ?= app:app
HOST ?= 127.0.0.1
PORT ?= 8000
IMAGE ?= ai-agent-platform:local

.PHONY: help venv install dev index test compile docker-build docker-run compose-up compose-down compose-logs compose-index

help:
	@echo "Available targets:"
	@echo "  make venv     Create a local virtual environment"
	@echo "  make install  Install Python dependencies"
	@echo "  make dev      Run the FastAPI dev server"
	@echo "  make index    Build the RAG document index"
	@echo "  make test     Run auth unit tests"
	@echo "  make compile  Compile Python files"
	@echo "  make docker-build  Build the Docker image"
	@echo "  make docker-run    Run the Docker image locally"
	@echo "  make compose-up    Run FastAPI and Postgres with Docker Compose"
	@echo "  make compose-down  Stop Docker Compose services"
	@echo "  make compose-logs  Tail Docker Compose logs"
	@echo "  make compose-index Build the RAG index inside Docker Compose"

venv:
	$(PYTHON) -m venv $(VENV)

install:
	@if [ -x "$(VENV_PYTHON)" ]; then \
		$(VENV_PYTHON) -m pip install -r requirements.txt; \
	else \
		$(PYTHON) -m pip install -r requirements.txt; \
	fi

dev:
	@if [ -x "$(VENV_UVICORN)" ]; then \
		$(VENV_UVICORN) $(APP) --reload --host $(HOST) --port $(PORT); \
	else \
		uvicorn $(APP) --reload --host $(HOST) --port $(PORT); \
	fi

index:
	@if [ -x "$(VENV_PYTHON)" ]; then \
		$(VENV_PYTHON) build_index.py; \
	else \
		$(PYTHON) build_index.py; \
	fi

test:
	@if [ -x "$(VENV_PYTHON)" ]; then \
		$(VENV_PYTHON) -m unittest test_auth.py; \
	else \
		$(PYTHON) -m unittest test_auth.py; \
	fi

compile:
	PYTHONPYCACHEPREFIX=/private/tmp/ai-agent-platform-pycache $(PYTHON) -m compileall app.py agent_graph.py build_index.py db.py schemas.py chains core graphs memory nodes rag scripts services state tools test_auth.py

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p $(PORT):8000 --env-file .env $(IMAGE)

compose-up:
	docker compose up --build

compose-down:
	docker compose down

compose-logs:
	docker compose logs -f

compose-index:
	docker compose run --rm app python build_index.py
