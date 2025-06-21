IMAGE_NAME = "tarobot"

.PHONY: build sync_ignore lint run stop logs pull update

run:
	docker compose up -d

build:
	docker compose build

sync_ignore:
	python bin/sync_ignore.py

lint:
	docker run --rm --volume $(CURDIR):/app --workdir /app pyfound/black:latest_release black .

stop:
	docker compose down

logs:
	docker compose logs -f

pull:
	git pull

update:
	make stop
	make pull
	make build
	make run