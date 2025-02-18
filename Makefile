IMAGE_NAME := ai_hedge_fund
CONTAINER_NAME := ai_hedge_fund_container

build:
	docker build -t $(IMAGE_NAME) .

run: WORKDIR = $(shell if [ "$(shell basename $(shell pwd))" = "ai-hedge-fund" ]; then pwd; else echo "Error: Not in ai-hedge-fund directory" >&2; exit 1; fi)
run: 
	docker run -d -v $(WORKDIR):/app/ --name $(CONTAINER_NAME) $(IMAGE_NAME) sleep 50000

up: build run

bash:
	docker exec -it $(CONTAINER_NAME) sh

stop:
	docker stop $(CONTAINER_NAME)

clean: stop
	docker rm $(CONTAINER_NAME)
	