VERSION := 3.0.0-rc0
export VERSION

MICROSERVICES = hyper desktopbuilder orchestrator controller auth backend frontend

all: deps gen test build docker
.PHONY: all

deps:
	go mod tidy
	$(MAKE) -C frontend deps

gen:
	$(MAKE) -C pkg gen
	$(foreach microservice,$(MICROSERVICES),$(MAKE) -C $(microservice) gen || exit 1;)

test:
	$(MAKE) -C pkg test
	$(foreach microservice,$(MICROSERVICES),$(MAKE) -C $(microservice) test || exit 1;)

build: test
	$(foreach microservice,$(MICROSERVICES),$(MAKE) -C $(microservice) build || exit 1;)

docker:
	$(foreach microservice,$(MICROSERVICES),$(MAKE) -C $(microservice) docker;)

docker-compose-up:
	docker-compose -f ./deployments/docker-compose/docker-compose.yml --project-directory . up -d

docker-compose-down:
	docker-compose -f ./deployments/docker-compose/docker-compose.yml --project-directory . down

dev:
	tmux new -s isardvdi-dev -n workspace -d
	# TODO: Cleanup microservice pkg
	$(foreach microservice,$(MICROSERVICES), if [ "$(microservice)" != "pkg" ]; then tmux neww -e $(shell echo $(microservice) | tr '[:lower:]' '[:upper:]')_DB_USR=dev -e $(shell echo $(microservice) | tr '[:lower:]' '[:upper:]')_DB_PWD=dev -n $(microservice); fi ;)
	$(foreach microservice,$(MICROSERVICES), if [ "$(microservice)" != "pkg" ]; then tmux send-keys -t "isardvdi-dev:$(microservice)" C-z 'cd isardvdi && $(MAKE) -C $(microservice) run' Enter; fi ;)
	tmux a -t isardvdi-dev:workspace
