VENV_PY := .venv/bin/python
BACKEND_HOST := 127.0.0.1
BACKEND_PORT := 8000
FRONTEND_PORT := 8501

backend:
	$(VENV_PY) -m uvicorn app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

frontend:
	$(VENV_PY) -m streamlit run streamlit_app.py --server.port $(FRONTEND_PORT)

dev:
	@bash -lc '\
	set -euo pipefail; \
	backend_cmd="$(VENV_PY) -m uvicorn app.main:app --reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)"; \
	frontend_cmd="$(VENV_PY) -m streamlit run streamlit_app.py --server.port $(FRONTEND_PORT)"; \
	echo "Starting backend: $$backend_cmd"; \
	( $$backend_cmd ) & BACK_PID=$$!; \
	sleep 1; \
	echo "Starting frontend: $$frontend_cmd"; \
	( $$frontend_cmd ) & FRONT_PID=$$!; \
	echo ""; \
	echo "Backend  : http://$(BACKEND_HOST):$(BACKEND_PORT)  (pid=$$BACK_PID)"; \
	echo "Frontend : http://localhost:$(FRONTEND_PORT)        (pid=$$FRONT_PID)"; \
	echo "Press Ctrl+C to stop both."; \
	cleanup(){ \
	  echo ""; \
	  echo "Stopping..."; \
	  kill $$FRONT_PID 2>/dev/null || true; \
	  kill $$BACK_PID 2>/dev/null || true; \
	  wait $$FRONT_PID 2>/dev/null || true; \
	  wait $$BACK_PID 2>/dev/null || true; \
	}; \
	trap cleanup INT TERM; \
	if help wait 2>/dev/null | grep -q -- "-n"; then \
	  wait -n $$BACK_PID $$FRONT_PID || true; \
	else \
	  while kill -0 $$BACK_PID 2>/dev/null && kill -0 $$FRONT_PID 2>/dev/null; do sleep 0.5; done; \
	fi; \
	cleanup; \
	'

doctor:
	bash scripts/doctor_env.sh

run:
	.venv/bin/python -m uvicorn app.main:app --reload --port 8000

streamlit:
	.venv/bin/python -m streamlit run streamlit_app.py

test:
	.venv/bin/pytest -q

docker-build:
	docker build -t medf-backend .

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down
