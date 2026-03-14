.PHONY: dev dev-bg down test test-unit test-int lint typecheck train tune format clean logs

dev:
	docker-compose up --build

dev-bg:
	docker-compose up --build -d

down:
	docker-compose down

test:
	pytest sentinel/tests/ -v --cov=sentinel/src --cov=sentinel/ml --cov-report=term-missing

test-unit:
	pytest sentinel/tests/unit/ -v

test-int:
	pytest sentinel/tests/integration/ -v

lint:
	ruff check sentinel/src/ sentinel/ml/ sentinel/workers/ sentinel/tests/

typecheck:
	mypy sentinel/src/ sentinel/ml/ sentinel/workers/

train:
	python -m sentinel.ml.train

tune:
	python -m sentinel.ml.tune

format:
	ruff format sentinel/src/ sentinel/ml/ sentinel/workers/ sentinel/tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true

logs:
	docker-compose logs -f backend celery_worker
