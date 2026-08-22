#!/bin/sh
set -e

#mkdir -p "/srv/Data/Tidekeeper"
#mkdir -p "/srv/Data/Cache"
#mkdir -p "/srv/Data/Music"

INITIAL_1="/srv/InitialData/Tidekeeper/.tidal-dl.json"
FINAL_1="/srv/Data/Tidekeeper/.tidal-dl.json"

if [ ! -f "$FINAL_1" ]; then
    echo "Copying initial .tidal-dl.json"
    mkdir -p "$(dirname "$FINAL_1")"
    cp "$INITIAL_1" "$FINAL_1"
fi

exec "$@"
