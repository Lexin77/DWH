run:
	docker-compose -f compose.yaml up -d --wait
	set -a; [ ! -f .env ] || . ./.env; set +a; uv run python -m scripts.init_raw_data

init:
	uv sync
