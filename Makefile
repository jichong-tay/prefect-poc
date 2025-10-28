.PHONY: help setup prefect-setup prefect-server prefect-start prefect-stop prefect-restart prefect-logs prefect-clean setup-concurrency test-auth run-flow run-ui deploy-flows start-workers run-distributed clean

help:
	@echo "Prefect POC - Available Commands:"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup              - Install dependencies with uv"
	@echo "  make prefect-setup      - Complete Prefect server setup (recommended)"
	@echo "  make setup-concurrency  - Configure server-side concurrency limits"
	@echo ""
	@echo "Prefect Server Commands:"
	@echo "  make prefect-server     - Start Prefect server (create new container)"
	@echo "  make prefect-start      - Start existing Prefect server container"
	@echo "  make prefect-stop       - Stop Prefect server container"
	@echo "  make prefect-restart    - Restart Prefect server container"
	@echo "  make prefect-logs       - View Prefect server logs"
	@echo "  make prefect-clean      - Stop and remove Prefect server container"
	@echo ""
	@echo "Distributed Workflow Commands:"
	@echo "  make deploy-flows       - Deploy flows to work pool"
	@echo "  make start-workers      - Start 3 workers (default)"
	@echo "  make start-workers N=5  - Start N workers"
	@echo "  make run-distributed    - Run distributed ETL flow"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test-auth          - Test Prefect authentication"
	@echo "  make run-flow           - Run production ETL flow (single flow)"
	@echo "  make run-ui             - Start Streamlit UI"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean              - Remove Python cache files"

setup:
	uv sync

prefect-setup:
	python scripts/setup_prefect_server.py

prefect-server:
	@if docker ps -a --format '{{.Names}}' | grep -q '^prefect-server$$'; then \
		echo "Container 'prefect-server' already exists. Use 'make prefect-start' to start it or 'make prefect-clean' to remove and recreate."; \
		exit 1; \
	fi
	docker run -d -p 4200:4200 --name prefect-server prefecthq/prefect:2.13.7-python3.10 prefect server start --host 0.0.0.0
	@echo "Prefect server started at http://localhost:4200"

prefect-start:
	docker start prefect-server
	@echo "Prefect server started at http://localhost:4200"

prefect-stop:
	docker stop prefect-server

prefect-restart:
	docker restart prefect-server
	@echo "Prefect server restarted at http://localhost:4200"

prefect-logs:
	docker logs -f prefect-server

prefect-clean:
	-docker stop prefect-server
	-docker rm prefect-server
	@echo "Prefect server container removed"

setup-concurrency:
	@export PREFECT_API_URL=http://localhost:4200/api && \
	python scripts/setup_concurrency_limit.py

test-auth:
	@export PREFECT_API_URL=http://localhost:4200/api && \
	python scripts/test_prefect_auth.py

run-flow:
	@export PREFECT_API_URL=http://localhost:4200/api && \
	python flows/prefect_flow.py

deploy-flows:
	@export PREFECT_API_URL=http://localhost:4200/api && \
	python flows/prefect_flow-worker-flow.py deploy

start-workers:
	@export PREFECT_API_URL=http://localhost:4200/api && \
	python scripts/start_workers.py --workers $(or $(N),3)

run-distributed:
	@export PREFECT_API_URL=http://localhost:4200/api && \
	python flows/prefect_flow-worker-flow.py run

run-ui:
	streamlit run streamlit/main.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true