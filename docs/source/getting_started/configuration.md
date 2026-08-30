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
    - If deploying via https (i.e: via a reverse proxy that upgrades all requests to https) and clients will access it at ```lighthouse.mydomain.com``` and the desired redirect port is ```9005``` this would be set to ```https://lighthouse.mydomain.com:9005/callback```.

!!! note "URI Redirects"
    It can be beneficial setting both the standard and IP versions of the address. I.e: using 'Redirect URI 1' for ```http://192.168.1.50/callback``` and 'Redirect URI 2' for ```https://lighthouse.mydomain.com/callback```.



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


## Tidekeeper Configuration (optional)

## Lighthouse-Client Configuration
