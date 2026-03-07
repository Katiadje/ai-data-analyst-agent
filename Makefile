.PHONY: install dev api app test lint format docker-up docker-down docker-build clean

# ── Setup ──────────────────────────────────────────────────────────────────────
install:
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev:
	pip install --upgrade pip
	pip install -r requirements.txt
	pre-commit install

# ── Run (local) ───────────────────────────────────────────────────────────────
api:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

app:
	streamlit run app/streamlit_app.py --server.port 8501

# Run both simultaneously (requires two terminals, or use docker-compose)
dev:
	@echo "Start the API: make api"
	@echo "Start the App: make app"
	@echo "Or use Docker: make docker-up"

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --tb=short --cov=agent --cov=api --cov-report=term-missing

# ── Code Quality ──────────────────────────────────────────────────────────────
lint:
	ruff check .

format:
	ruff format .

lint-fix:
	ruff check --fix .
	ruff format .

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# ── Terraform ─────────────────────────────────────────────────────────────────
tf-init:
	cd infra && terraform init

tf-plan:
	cd infra && terraform plan -var-file="terraform.tfvars"

tf-apply:
	cd infra && terraform apply -var-file="terraform.tfvars" -auto-approve

tf-destroy:
	cd infra && terraform destroy -var-file="terraform.tfvars" -auto-approve

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned."
