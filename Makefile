# TicketTriage Makefile
# Accepts DOMAIN parameter, defaulting to saas (e.g. `make data DOMAIN=ecommerce`)

DOMAIN ?= saas
PYTHON ?= python
NPM ?= npm

.PHONY: all help data train api web test clean

help:
	@echo "TicketTriage build & run targets:"
	@echo "  make data  [DOMAIN=name] - Generate synthetic ticket dataset"
	@echo "  make train [DOMAIN=name] - Train and evaluate multi-label models"
	@echo "  make test  [DOMAIN=name] - Run backend test suite (unit + SLA + API)"
	@echo "  make api   [DOMAIN=name] - Start FastAPI backend service"
	@echo "  make web                 - Start Vite React frontend"
	@echo "  make clean               - Clean cache files"

data:
	$(PYTHON) ml-service/data/generate_synthetic.py --domain $(DOMAIN) --count 10000

train:
	$(PYTHON) ml-service/training/train.py --domain $(DOMAIN)

test:
	cd ml-service && $(PYTHON) -m pytest tests/ -v

api:
	cd ml-service && $(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

web:
	cd frontend && $(NPM) run dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
