run:
	docker compose -f compose.yaml up -d --wait
	set -a; [ ! -f .env ] || . ./.env; set +a; .venv/bin/python -m scripts.init_raw_data

init:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
