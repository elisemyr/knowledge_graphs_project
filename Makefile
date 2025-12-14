.PHONY: help run docker-build docker-run clean venv install lint format tree

# Image tag (override with: make docker-build TAG=myorg/myapp:dev)
TAG ?= graph-api:dev

help:
	@echo "Commands:"
	@echo "  make venv           Create local virtualenv (.venv)"
	@echo "  make install        Install requirements into .venv"
	@echo "  make run            Run FastAPI (uvicorn) on :8000"
	@echo "  make docker-build   Build Docker image (TAG=$(TAG))"
	@echo "  make docker-run     Run Docker container on :8000"
	@echo "  make lint           Run pylint (if configured)"
	@echo "  make format         Run black code formatter"
	@echo "  make clean          Remove caches and temp files"
	@echo "  make tree           Show project tree (depth 3)"

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
	@. .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t $(TAG) .

docker-run:
	docker run --rm -it -p 8000:8000 --env-file .env $(TAG)

lint:
	@if command -v .venv/bin/pylint >/dev/null 2>&1; then \
		.venv/bin/pylint ./backend/ || true; \
	else echo "pylint not installed (add to requirements.txt)"; fi

format:
	@if command -v .venv/bin/black >/dev/null 2>&1; then \
		.venv/bin/black app -l 120; \
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