.PHONY: test lint up down cluster deploy
test: ; pytest -q
lint: ; ruff check app tests
up: ; docker compose up --build -d
down: ; docker compose down -v
cluster: ; kind create cluster --name docscan
deploy: ; helm upgrade --install docscan helm/docscan -n docscan --create-namespace
