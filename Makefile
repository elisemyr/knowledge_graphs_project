.PHONY: help run docker-build docker-run clean venv install lint format tree

# Image tag (override with: make docker-build TAG=myorg/myapp:dev)
TAG ?= graph-api:universityplanner-project
REPO ?= docker.io/asabourdin
GRAPH_API_PORT ?= 8001



help:
	@echo "Commands:"
	@echo "  make venv                 Create local virtualenv (.venv)"
	@echo "  make install              Install requirements into .venv"
	@echo "  make run                  Run FastAPI (uvicorn) on :$(GRAPH_API_PORT)"
	@echo "  make docker-build         Build Docker image (REPO/TAG=$(REPO)/$(TAG))"
	@echo "  make docker-build         Push Docker image (REPO/TAG=$(REPO)/$(TAG)) to docker hub"
	@echo "  make docker-run           Run Docker container on :$(GRAPH_API_PORT)"
	@echo "  make docker-compose-up    Run docker compose up"
	@echo "  make docker-compose-down  Run docker compose down"
	@echo "  make lint                 Run pylint (if configured)"
	@echo "  make format               Run black code formatter"
	@echo "  make clean                Remove caches and temp files"
	@echo "  make tree                 Show project tree (depth 3)"

venv:
	@if [ ! -d ".venv" ]; then \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install --upgrade pip; \
		echo "Created .venv"; \
	else echo ".venv already exists"; fi
	@echo "To activate: source .venv/bin/activate"

install: venv
	@. .venv/bin/activate && pip install -r requirements.txt

run:
	@. .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port $(GRAPH_API_PORT) --reload

docker-build:
	docker build -t $(REPO)/$(TAG) .

docker-push:
	docker push $(REPO)/$(TAG)

docker-run:
	@if [ -f ".env" ]; then \
		docker run --rm -it -p $(GRAPH_API_PORT):$(GRAPH_API_PORT) --env-file .env $(REPO)/$(TAG) ; \doc
	else echo ".env is missing"; fi

docker-compose-up:
	@if [ -f ".env" ]; then \
	    docker compose --env-file .env up  --force-recreate ; \
	else echo ".env is missing"; fi

docker-compose-down:
	docker compose down

lint:
	@if command -v .venv/bin/pylint >/dev/null 2>&1; then \
		.venv/bin/pylint ./backend/ || true; \
	else echo "pylint not installed (add to requirements.txt)"; fi

format:
	@if command -v .venv/bin/black >/dev/null 2>&1; then \
		.venv/bin/black ./backend/ -l 120; \
	else echo "black not installed (add to requirements.txt)"; fi

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} \; || true
	find . -type f -name "*.pyc" -delete || true

tree:
	@if command -v tree >/dev/null 2>&1; then \
		tree -L 3 -I "node_modules|dist|.git|.venv|__pycache__"; \
	else \
		find . -maxdepth 3 -type d -not -path '*/\.*' | sort; \
	fi