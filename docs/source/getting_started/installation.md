# Installation
## Prerequisites
Obtain a computer that has:

- Internet access
- a recent version of [docker compose](https://docs.docker.com/compose/install) installed (preferably the Docker Compose 'plugin').

The rest of this guide will assume you are using Linux but the broad steps should work with Windows as well.

## Setup the docker image
Pick a folder to do the rest of the setup in. It's common to use something like ```/srv/docker/lighthouse``` but the location doesn't matter. Don't forget to use your path when the rest of this guide refers to ```{path}/lighthouse```.

Make the folder:
```
mkdir -p {path}/lighthouse
```

Obtain the [docker compose file](https://github.com/redraven2459/lighthouse/blob/main/compose.yaml):
```
cd {path}/lighthouse
wget https://raw.githubusercontent.com/redraven2459/lighthouse/refs/heads/main/compose.yaml
```

Obtain the [.env file](https://raw.githubusercontent.com/redraven2459/lighthouse/refs/heads/main/.env.example):
```
cd {path}/lighthouse
wget -O .env https://raw.githubusercontent.com/redraven2459/lighthouse/refs/heads/main/.env.example
```

Pull the docker image:
```
docker compose pull
```

Proceed to [configuration](configuration.md).
