# Recommended Development Environment Setup
## Overview
Developing contributions for Lighthouse is quite simple:

1. Obtain the prerequisites
2. Clone the repository
3. Download dependencies
4. Start development server(s)
5. Confirm everything works

Whilst it is theoretically possible to develop Lighthouse-Server and Lighthouse-Client separately it is considered best practice to set-up a combined development environment as Lighthouse-Client relies on Lighthouse-Server which in turn relies on Tidekeeper and internet access.

This guide assumes you are using Linux but it should be possible to follow on Windows as well.

## Prerequisites
Obtain a computer that is capable of accessing the internet and has the following installed:

1. a recent version of [python](https://wiki.python.org/moin/BeginnersGuide(2f)Download.html)
2. a recent version of [flutter's SDK](https://docs.flutter.dev/install/)
3. a recent version of [git](https://git-scm.com/install/)
4. a text editor or desired IDE of your choice
5. (optionally): a web browser

Personally, I used:

- the version of python that was packaged with my Linux distribution (3.14.6)
- the 'custom setup' of flutter (because I don't use VSCode)
- the docker compose 'plugin' (because I don't use docker's GUI)
- [Pulsar](https://pulsar-edit.dev/)
- Chromium

!!! note
    1. Internet access is required for cloning the repository, downloading the dependencies, and testing Lighthouse-Server's interactions with Tidal's API.
    2. Python is required for developing Lighthouse-Server and these docs.
    3. Flutter is required for developing Lighthouse-Client.


You will also need an active Tidal account and a client-id token for a Tidal App from the Tidal Developers Portal. This is the same token that is used when installing Lighthouse normally - see the Lighthouse [configuration guide](../getting_started/configuration.md) for more details on obtaining this token.

!!! note
    Each instance of Lighthouse uses a unique client-id token to enable continuity of other instances if that client-id token is banned.

Pick a folder to do the rest of the setup in. I personally prefer using something like ```/home/{username}/Documents/Lighthouse-Project``` but the location doesn't matter. Don't forget to use your path when the rest of this guide refers to ```{path}/Lighthouse-Project```.

## Clone the repository

Clone the repository using Git:
``` sh
cd {path}/Lighthouse-Project
git clone https://github.com/redraven2459/lighthouse.git
```

Or by going to the [repository](https://github.com/redraven2459/lighthouse.git), clicking the green code button, downloading a ZIP file of the contents, and then extracting it in the right place.

The repository should not be available locally at: ```{path}/Lighthouse-Project/lighthouse```

## Download Dependencies
Lighthouse-Server and Lighthouse-Client both have dependencies that need to be installed.

Install Lighthouse-Clients dependencies:
```
cd {path}/Lighthouse-Project/lighthouse/Lighthouse-Client/src/lighthouse_client
flutter pub get
```

Create a venv for Lighthoue-Server:
```
cd {path}/Lighthouse-Project
python -m venv venv
```

Active the venv:
```
source venv/bin/activate
```

Install the Lighthouse-Server dependencies into the venv:
```
cd {path}/Lighthouse-Project/lighthouse/Lighthouse-Server
python -m pip install -e .
```

Install the docs dependencies into the venv:
```
python -m pip install zensical
```

## Configure environment
It is necessary to create a local ```Data``` directory. I.e:
```
cd {path}/Lighthouse-Project
mkdir Data
```

You will also need to configure Tidekeeper's config file and place it in ```{path}/Lighthouse-Project/Data/Tidekeeper```- see the Lighthouse [configuration guide](../getting_started/configuration.md) for more details on configuring the Tidekeeper config file.

Lighthouse-Server normally depends on environment variables that are passed to the container via a .env file. When developing Lighthouse-Server it's necessary to provide the .env file locally, i.e: ```{path}/Lighthouse-Project/lighthouse/Lighthouse-Server/src/lighthouse_server/.env``` - see the Lighthouse [configuration guide](../getting_started/configuration.md) for more details on configuring the ```.env```.

It can also be worth changing ```{path}/Lighthouse-Project/lighthouse/Lighthouse-Server/src/lighthouse_server/database_api.py```'s ```DatabaseAPI()```'s ```self._prototyping_mode = False``` to ```self._prototyping_mode = True```. When set, SQLModel will automatically build the database without invoking the alembic framework when the database schema changes and the existing ```{path}/Lighthouse-Project/Data/database/database.db``` file is deleted.

## Start development server(s)
Run each of the following code blocks in separate consoles:

docs:
```
cd {path}/Lighthouse-Project
source venv/bin/activate
cd {path}/Lighthouse-Project/lighthouse/docs
python -m zensical serve -a localhost:3000
```

Lighthouse-Server:
```
cd {path}/Lighthouse-Project
source venv/bin/activate
python -m fastapi dev {path}/Lighthouse-Project/lighthouse/Lighthouse-Server/src/lighthouse_server/__main__.py
```

Lighthouse-Client:
```
cd {path}/Lighthouse-Project/lighthouse/Lighthouse-Client/src/lighthouse_client
flutter run
```

## Confirm everything works
Check the docs load by opening a web browser and going to ```127.0.0.1:3000/```. Confirm the docs load.

Check Lighthouse-Server has started by opening a web browser and going to ```127.0.0.1:8000/docs/```. Confirm the OpenAPI docs for Lighthouse-Server load.

Check Lighthouse-Client has started (depending on the option selected during ```flutter run``` it should either be open in a web browser or an app on the desktop).

You should now be ready to develop Lighthouse.
