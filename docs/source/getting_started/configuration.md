# Configuration
## Overview
Configuring Lighthouse requires a few files to be edited. Following the sections in order is recommended but not mandatory.

## Prerequisites
Lighthouse requires an active Tidal account

## Tidal API Configuration
Lighthouse requires a client-id token and redirect-uri to be created via Tidal's developer website to function:

1. Go to [Tidal's Developer Portal](https://developer.tidal.com/).
2. Log in / create an account.
3. Click 'dashboard' in the top right.
4. Click '+ Create New App'.
5. Use a random name for the app name (ideally not linked to Lighthouse) - this isn't used anywhere other than this developer portal.
6. Click 'Create App'.
7. Confirm a token exists for 'Client ID'.
8. Click 'Settings'.
9. Click 'Edit'.
10. Set 'Redirect URI 1' to ```{protocol}://{address}:{redirect-port}/callback``` - see the URI Examples below.
11. Click 'Save'.


!!! warning
    The Redirect URI port must be different to the port's used to access Lighthouse-Server and Lighthouse-Client. It is a good idea to set it to random like ```9001```.

    The Client-ID token and URI Redirect used later in the 'Compose Configuration' section needs to match the Client-ID and one of the URI Redirects set here perfectly. Failure to do so will prevent Lighthouse from communicating with Tidal's API.

!!! example "URI Examples"
    - If deploying via http (i.e: no reverse proxy) and clients will access Lighthouse-Server at ```192.168.1.50``` and the desired redirect port is ```9001``` it would be set to ```http://192.168.1.50:9001/callback```.
    - If deploying via https (i.e: via a reverse proxy that upgrades all requests to https) and clients will access Lighthouse-Server at ```server.lighthouse.mydomain.com``` and the desired redirect port is ```9005``` this would be set to ```https://server.lighthouse.mydomain.com:9005/callback```.

!!! note "URI Redirects"
    It can be beneficial setting both the standard and IP versions of the address. I.e: using 'Redirect URI 1' for ```http://192.168.1.50:9001/callback``` and 'Redirect URI 2' for ```https://lighthouse.mydomain.com:9001/callback```.



## Environment Configuration
Open the ```.env``` file downloaded during installation (i.e: ```{path}/lighthouse/.env```):

1. Set ```LIGHTHOUSE_SERVER_COUNTRY_CODE``` to a suitable value (i.e: ```"US"```, ```"GB"```, etc).
2. Set ```LIGHTHOUSE_SERVER_TIDAL_API_CLIENT_ID``` as per the Client ID token generated previously (i.e: ```"ABCDEF...123"```).
3. Ignore ```LIGHTHOUSE_SERVER_TIDAL_API_SCOPES```.
3. Set ```LIGHTHOUSE_SERVER_TIDAL_API_REDIRECT_ADDRESS``` to the desired address (i.e: ```"192.168.1.50"```).
4. Set ```LIGHTHOUSE_SERVER_TIDAL_API_REDIRECT_PORT``` to the desired port (i.e: ```9001```).
5. Ignore ```LIGHTHOUSE_SERVER_DATA_PATH``` unless developing Lighthouse locally. If developing locally set it to whichever path you want data to be stored in.
6. Ignore ```LIGHTHOUSE_SERVER_TIDEKEEPER_PATH``` unless you want to use a specific local installation of Tidekeeper. If you want to use a specific local installation of Tidekeeper enter the path here.

## Compose Configuration
The default configuration for the ```compose.yaml``` file downloaded during installation works well but can be tweaked. Consider changing the following settings:

- ```user``` in lighthouse_server to a desired UID:GID if you do not want to run it as root.
- ```ports``` in lighthouse_server and/or lighthouse_client if your existing setup already uses ports 9990-9992.
- ```volumes```in lighthouse_server to a desired local path. By default this creates a folder called ```data``` next to the ```compose.yaml```.

!!! note
    - the port marked as ```9990``` in ```9990:8000``` is the port used for accessing Lighthouse-Server.
    - the ports marked as ```9992``` in ```9992:80``` is the port used for accessing Lighthouse-Client.
    - the ports marked as ```9991:9991``` need to match the ports used for the Redirect URI port.


!!! note
    It can be advantageous to map the directories within /srv/Data more explicitly if your media hosting solution lives in a different filepath. For example:
    ```
    volumes:
      - ./data:/srv/Data
      - ./data/Database:/srv/Data/Database
      - ./data/Cache:/srv/Data/Cache
      - ./data/Music/Music:/srv/Data/Music/Music
      - ./data/Music/Video:/srv/Data/Music/Video
    ```
    ```./data/Music/Music``` and ```./data/Music/Video``` can then be sym-linked to your desired media hosting file path.

## Tidekeeper Configuration (optional)
The default Tidekeeper configuration created during the first run of Lighthouse works well but can be tweaked. The configuration file is created in ```/srv/Data/Tidekeeper/.tidal-dl.json``` (i.e: ```{path}/lighthouse/data/Tidekeeper.tidal-dl.json```) using the [template](https://github.com/redraven2459/lighthouse/blob/main/Lighthouse-Server/docker/.tidal-dl.json.example) available in the repository. See [Tidekeeper](https://github.com/OpenNerdz/tidekeeper) for details about further configuring this file.

!!! warning
    Lighthouse expects the ```albumFolderFormat```, ```trackFileFormat```, and ```videoFileFormat``` values to be as defined in the template. Changing these values will cause Lighthouse to catastrophically fail.

## Reverse proxy Configuration (optional)
If using a reverse proxy you will be responsible for proxying:

- Lighthouse-Server's address
- Lighthouse-Server's standard port and redirect port
- Lighthouse-Client's address and port

## Lighthouse-Client Configuration
When using Lighthouse for the first time (or if a devices cache is cleared) it will be necessary to specify the URI of Lighthouse-Server. It will automatically try to connect via HTTPS and failing that HTTP.

!!! example
    - ```lighthouse.mydomain.com```.
    - ```192.168.1.50:9000```.
    - ```https://lighthouse.mydomain.com```.

## Startup / Shutdown
The installation and configuration of Lighthouse should now be complete.

Start Lighthouse by running:
```
cd {path}/lighthouse
docker compose up -d
```

Stop Lighthouse by running:
```
cd {path}/lighthouse
docker compose down
```

Navigate to the configured address and port to check you are greeted by the Lighthouse UI (i.e: ```{address of docker host}:{Lighthouse-Client port}``` or ```{Lighthouse-Client address}:{Lighthouse-Client port}``` if reverse proxied).
