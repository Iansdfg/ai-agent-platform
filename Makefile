PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_UVICORN := $(VENV)/bin/uvicorn
APP ?= app:app
HOST ?= 127.0.0.1
PORT ?= 8000
IMAGE ?= ai-agent-platform:local
AWS_ACCOUNT_ID ?= 347387311652
AWS_REGION ?= us-east-1
ECR_REPOSITORY ?= ai-agent-platform
ECS_CLUSTER ?= ai-agent-platform-cluster
ECS_SERVICE ?= ai-agent-platform-service
TASK_DEFINITION_FILE ?= ecs-task-definition.json
IMAGE_TAG ?= amd64-$(shell date +%Y%m%d%H%M%S)
ECR_IMAGE_URI := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(ECR_REPOSITORY):$(IMAGE_TAG)

.PHONY: help venv install dev index test compile docker-build docker-run compose-up compose-down compose-logs compose-index aws aws-deploy deploy

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
	@echo "  make aws-deploy    Build, push, and deploy the app to ECS"
	@echo "  make aws deploy    Alias for make aws-deploy"

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

aws:
	@if [ "$(filter deploy,$(MAKECMDGOALS))" = "deploy" ]; then \
		$(MAKE) aws-deploy; \
	else \
		echo "Usage: make aws deploy"; \
		exit 2; \
	fi

deploy:
	@:

aws-deploy:
	@set -e; \
	echo "Deploying $(ECR_IMAGE_URI) to $(ECS_CLUSTER)/$(ECS_SERVICE)"; \
	echo "Logging in to ECR"; \
	aws ecr get-login-password --region $(AWS_REGION) | docker login \
		--username AWS \
		--password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com; \
	echo "Building Docker image"; \
	docker build --platform linux/amd64 -t $(ECR_REPOSITORY):$(IMAGE_TAG) .; \
	echo "Tagging Docker image"; \
	docker tag $(ECR_REPOSITORY):$(IMAGE_TAG) $(ECR_IMAGE_URI); \
	echo "Pushing Docker image"; \
	docker push $(ECR_IMAGE_URI); \
	echo "Updating $(TASK_DEFINITION_FILE)"; \
	$(PYTHON) -c 'import json; p="$(TASK_DEFINITION_FILE)"; image="$(ECR_IMAGE_URI)"; data=json.load(open(p)); data["containerDefinitions"][0]["image"]=image; open(p,"w").write(json.dumps(data, indent=2) + "\n")'; \
	echo "Registering ECS task definition"; \
	task_def_arn=$$(aws ecs register-task-definition \
		--cli-input-json file://$(TASK_DEFINITION_FILE) \
		--region $(AWS_REGION) \
		--query "taskDefinition.taskDefinitionArn" \
		--output text); \
	echo "Registered $$task_def_arn"; \
	echo "Updating ECS service"; \
	aws ecs update-service \
		--cluster $(ECS_CLUSTER) \
		--service $(ECS_SERVICE) \
		--task-definition $$task_def_arn \
		--force-new-deployment \
		--region $(AWS_REGION) >/dev/null; \
	echo "Waiting for ECS service to become stable"; \
	aws ecs wait services-stable \
		--cluster $(ECS_CLUSTER) \
		--services $(ECS_SERVICE) \
		--region $(AWS_REGION); \
	echo "Deployment complete: $$task_def_arn"
