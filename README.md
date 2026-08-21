# Lighthouse
A framework for music hoarding and aquistion - powered by Tidekeeper.

# Goals
Lighthouse aims to provide a means of:
- Requesting artists and albums to be acquired from Tidal (via Tidekeeper)

# Installation
Lighthouse is intended to be ran as a docker service via docker compose. The Lighthouse docker image bundles the Lighthouse-Client, the Lighthouse-Server, and Tidekeeper into a single deployment.

Note:
The .env file requires 4 values to align with a Tidal 'app'. The 'app' can be created for free by:
- Creating an account at https://developer.tidal.com/
- Clicking 'Create New App'
- Copying 'Client ID' into the .env
- Clicking 'Settings'
- Ensure 'Scopes' matches scopes in the .env
- Ensure Redirect URI points to the host of the docker image (i.e: http://192.168.0.5/callback or http://lighthouse.myhomelab.com/callback) and matches the .env (i.e: "192.168.4.115" or "lighthouse.myhomelab.com")
- Ensure Redirect URI points to the host port of the docker image (i.e: http://192.168.0.5:8080/callback and matches the .env (i.e: 8080)
