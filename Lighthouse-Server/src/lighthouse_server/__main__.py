import subprocess, os, json, inspect
from enum import Enum
from datetime import datetime, timedelta, UTC
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Session, select

from lighthouse_server.tasks import *
from lighthouse_server.settings import Settings, Logger
from lighthouse_server.lighthouse_api import LighthouseAPI
from lighthouse_server.models import *

from lighthouse_server.database_api import DatabaseAPI

API_MAJOR_VERSION = 0
API_MINOR_VERSION = 1
API_PATCH_VERSION = 0
API_VERSION = str(API_MAJOR_VERSION) + "." + str(API_MINOR_VERSION) + "." + str(API_PATCH_VERSION)

settings = Settings()


def emptyFunction(task_id):
    return

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start startup
    Logger.info("lighthouse_server startup start")
    # Configure tidekeeper
    Logger.info("lighthouse_server startup: configuring Tidekeeper")
    with open(settings.tidekeeper_config_path + "/.tidal-dl.json", "r") as file:
        data = json.load(file)
    data["downloadPath"] = settings.tidekeeper_music_path
    with open(settings.tidekeeper_config_path + "/.tidal-dl.json", "w") as file:
        json.dump(data, file, indent=4)
    # TaskHandler startup
    Logger.info("lighthouse_server startup: initialising TaskHandler")
    TaskHandler().startup()
    # Startup Scan
    Logger.info("lighthouse_server startup: performing startup scan")
    startup_task_description = "Startup scan"
    startup_task_id = TaskHandler().start_task(target=emptyFunction, description=startup_task_description)
    LighthouseAPI().scanAll(startup_task_id, endpoint=True)
    # Finish startup
    Logger.info("lighthouse_server startup complete")
    yield
    Logger.info("lighthouse_server shutdown start")
    TaskHandler().shutdown()
    Logger.info("lighthouse_server shutdown complete")

app = FastAPI(
    title="LIGHTHOUSE_SERVER",
    description="API for LIGHTHOUSE_SERVER",
    version=API_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"]
)

@app.get("/", response_model=RootRead)
async def root():
    Logger.info("Root endpoint accessed")
    return RootRead(api_version=API_VERSION, database_version=DATABASE_VERSION)

# Helper functions
def get_artist_information_response(artist_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
        if artist is None:
            raise HTTPException(404, "Artist not found")
        primary_albums = artist.primary_albums
        secondary_albums = artist.secondary_albums
        primary_videos = artist.primary_videos
        secondary_videos = artist.secondary_videos

        primary_album_informations = []
        secondary_album_informations = []
        for album in primary_albums:
            primary_album_informations.append(AlbumInformationResponse(album=album, tracks=album.tracks))
        for album in secondary_albums:
            secondary_album_informations.append(AlbumInformationResponse(album=album, tracks=album.tracks))

    artist_information = ArtistInformationResponse(
        artist=artist,
        primary_albums_information=primary_album_informations,
        secondary_albums_information=secondary_album_informations,
        primary_videos=primary_videos,
        secondary_videos=secondary_videos,
    )
    return artist_information

def get_album_information_response(album_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one_or_none()
        if album is None:
            raise HTTPException(404, "Album not found")
        tracks = album.tracks
    album_information = AlbumInformationResponse(
        album=album,
        tracks=tracks,
    )
    return album_information


# Functional endpoints
@app.get("/search/artists", response_model=TaskRead)
async def search_artists_post(artist_name: str):
    task_description = "Search for artist(s): " + str(artist_name)
    task_id = TaskHandler().start_task(target=LighthouseAPI().searchForArtistAndMetadata, description=task_description, text=artist_name)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

# Task endpoints
@app.get("/tasks", response_model=list[TaskRead])
async def get_tasks(
    offset: int = 0,
    limit: int = 50,
    exclude_expired: bool = False,
    description: str = None,
    exclude_description: str = None,
    status_code: int = None,
    exclude_status_code: int = None,
):
    with Session(DatabaseAPI().engine) as session:
        statement = select(Task)
        conditions = []
        if exclude_expired == True:
            conditions.append(Task.expire_time > datetime.now(UTC))
        if description != None:
            conditions.append(func.lower(Task.description).contains(description.lower()))
        if exclude_description != None:
            conditions.append(~func.lower(Task.description).contains(exclude_description.lower()))
        if status_code != None:
            conditions.append(Task.status_code == status_code)
        if exclude_status_code != None:
            conditions.append(Task.status_code != exclude_status_code)
        tasks = session.exec(statement.where(*conditions).order_by(Task.id.desc()).offset(offset).limit(limit)).all()
    return tasks

@app.get("/tasks/{id}", response_model=TaskRead)
async def get_task(id: int):
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == id)).one_or_none()
    if task is None:
        raise HTTPException(404, "Artist not found")
    return task


# Artist endpoints
@app.get("/artists", response_model=list[ArtistRead])
async def get_artists(
    offset: int = 0,
    limit: int = 50,
    monitored: bool = None
):
    with Session(DatabaseAPI().engine) as session:
        statement = select(Artist)
        conditions = []
        if monitored != None:
            conditions.append(Artist.monitored == monitored)
        artists = session.exec(statement.where(*conditions).order_by(Artist.name).offset(offset).limit(limit)).all()
        return artists

@app.get("/artists/{artist_tidal_id}", response_model=ArtistRead)
async def get_artist(artist_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
        if artist is None:
            raise HTTPException(404, "Artist not found")
        return artist

@app.patch("/artists/{artist_tidal_id}", response_model=ArtistRead)
async def patch_artist(artist_tidal_id: int, artist: ArtistUpdate):
    with Session(DatabaseAPI().engine) as session:
        db_artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
        if db_artist is None:
            raise HTTPException(404, "Artist not found")
        artist_data = artist.model_dump(exclude_unset=True)
        db_artist.sqlmodel_update(artist_data)
        session.commit()
        session.refresh(db_artist)
        return db_artist

@app.get("/artists/{artist_tidal_id}/information", response_model=ArtistInformationResponse)
async def get_artist_artist_information(artist_tidal_id: int):
    return get_artist_information_response(artist_tidal_id)

@app.get("/artists/{artist_tidal_id}/image", response_class=FileResponse)
async def get_artist(artist_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
        if artist is None:
            raise HTTPException(404, "Artist not found")
        if artist.image_cache_id is None:
            raise HTTPException(404, "Artist image does not exist")
        image_path = settings.cache_path + "/" + artist.image_cache_id
    return FileResponse(image_path)

@app.get("/artists/{artist_tidal_id}/primary_albums", response_model=list[AlbumRead])
async def get_artist_primary_albums(artist_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
        if artist is None:
            raise HTTPException(404, "Artist not found")
        albums = artist.primary_albums
    return albums

@app.get("/artists/{artist_tidal_id}/secondary_albums", response_model=list[AlbumRead])
async def get_artist_secondary_albums(artist_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
        if artist is None:
            raise HTTPException(404, "Artist not found")
        albums = artist.secondary_albums
    return albums

@app.get("/artists/{artist_tidal_id}/scan/content", response_model=TaskRead)
async def scrape_artist_content(artist_tidal_id: int):
    task_description = "Scan Artist(content): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanArtistAll, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scan/albums", response_model=TaskRead)
async def scan_artist_albums(artist_tidal_id: int):
    task_description = "Scan Artist(albums): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanArtistAlbums, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scan/videos", response_model=TaskRead)
async def scan_artist_videos(artist_tidal_id: int):
    task_description = "Scan Artist(videos): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanArtistVideos, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scrape/content", response_model=TaskRead)
async def scrape_artist_content(artist_tidal_id: int):
    task_description = "Scrape Artist(content): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeArtistContent, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scrape/tracks", response_model=TaskRead)
async def scrape_artist_tracks(artist_tidal_id: int):
    task_description = "Scrape Artist(tracks): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeArtistTracks, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scrape/albums", response_model=TaskRead)
async def scrape_artist_albums(artist_tidal_id: int):
    task_description = "Scrape Artist(albums): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeArtistAlbums, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scrape/videos", response_model=TaskRead)
async def scrape_artist_videos(artist_tidal_id: int):
    task_description = "Scrape Artist(videos): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeArtistVideos, description=task_description, artist_tidal_id=artist_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/acquire/content", response_model=TaskRead)
async def acquire_artist(
    artist_tidal_id: int,
    force: bool = False,
):
    task_description = "Acquire Artist(content): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireArtist, description=task_description, artist_tidal_id=artist_tidal_id, force=force, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/acquire/tracks", response_model=TaskRead)
async def acquire_artist_tracks(
    artist_tidal_id: int,
    force: bool = False,
):
    task_description = "Acquire Artist(tracks): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireArtistTracks, description=task_description, artist_tidal_id=artist_tidal_id, force=force, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/acquire/videos", response_model=TaskRead)
async def acquire_artist_videos(
    artist_tidal_id: int,
    force: bool = False,
):
    task_description = "Acquire Artist(videos): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireArtistVideos, description=task_description, artist_tidal_id=artist_tidal_id, force=force, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/artists/{artist_tidal_id}/scrape_and_acquire/all", response_model=TaskRead)
async def scrape_and_acquire_artist(artist_tidal_id: int):
    task_description = "Scrape and Acquire Artist(All): " + str(artist_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeAndAcquireArtistAll, description=task_description, artist_tidal_id=artist_tidal_id)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task


# Album endpoints
@app.get("/albums", response_model=list[AlbumRead])
async def get_albums(offset: int = 0, limit: int = 50):
    with Session(DatabaseAPI().engine) as session:
        albums = session.exec(select(Album).offset(offset).limit(limit)).all()
        return albums

@app.get("/albums/{album_tidal_id}", response_model=AlbumRead)
async def get_album(album_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
        return album

@app.patch("/albums/{album_tidal_id}", response_model=AlbumRead)
async def patch_album(album_tidal_id: int, album: AlbumUpdate):
    with Session(DatabaseAPI().engine) as session:
        db_album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one_or_none()
        if db_album is None:
            raise HTTPException(404, "Album not found")
        album_data = album.model_dump(exclude_unset=True)
        db_album.sqlmodel_update(album_data)
        session.commit()
        session.refresh(db_album)
        return db_album

@app.get("/albums/{album_tidal_id}/information", response_model=AlbumInformationResponse)
async def get_album_album_information(album_tidal_id: int):
    return get_album_information_response(album_tidal_id)

@app.get("/albums/{album_tidal_id}/image", response_class=FileResponse)
async def get_artist(album_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one_or_none()
        if album is None:
            raise HTTPException(404, "Album not found")
        if album.image_cache_id is None:
            raise HTTPException(404, "Album image does not exist")
        image_path = settings.cache_path + "/" + album.image_cache_id
    return FileResponse(image_path)

@app.get("/albums/{album_tidal_id}/tracks", response_model=list[TrackRead])
async def get_album_tracks(album_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
        tracks = album.tracks
        return tracks

@app.get("/albums/{album_tidal_id}/scrape/tracks", response_model=TaskRead)
async def scrape_album_tracks(album_tidal_id: int):
    task_description = "Scrape Album Tracks: " + str(album_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeAlbumTracks, description=task_description, album_tidal_id=album_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/albums/{album_tidal_id}/scan/tracks", response_model=TaskRead)
async def scan_album(album_tidal_id: int):
    task_description = "Scan Album: " + str(album_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanAlbum, description=task_description, album_tidal_id=album_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/albums/{album_tidal_id}/acquire/tracks", response_model=TaskRead)
async def acquire_album(
    album_tidal_id: int,
    force: bool = False,
):
    task_description = "Acquire Album: " + str(album_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireAlbumTracks, description=task_description, album_tidal_id=album_tidal_id, force=force, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

# Track endpoints
@app.get("/tracks", response_model=list[TrackRead])
async def get_tracks(offset: int = 0, limit: int = 50):
    with Session(DatabaseAPI().engine) as session:
        tracks = session.exec(select(Track).offset(offset).limit(limit)).all()
        return tracks

@app.get("/tracks/{track_tidal_id}", response_model=TrackRead)
async def get_track(track_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one()
        return track

@app.patch("/tracks/{track_tidal_id}", response_model=TrackRead)
async def patch_track(track_tidal_id: int, track: TrackUpdate):
    with Session(DatabaseAPI().engine) as session:
        db_track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one_or_none()
        if db_track is None:
            raise HTTPException(404, "Track not found")
        track_data = track.model_dump(exclude_unset=True)
        db_track.sqlmodel_update(track_data)
        session.commit()
        session.refresh(db_track)
        return db_track

@app.get("/tracks/{track_tidal_id}/album", response_model=AlbumRead)
async def get_track_parent(track_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one()
        album = session.exec(select(Album).where(Album.tidal_id == track.album_tidal_id)).one()
        return album

@app.get("/tracks/{track_tidal_id}/scan", response_model=TaskRead)
async def scan_track(track_tidal_id: int):
    task_description = "Scan Track: " + str(track_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanTrack, description=task_description, track_tidal_id=track_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/tracks/{track_tidal_id}/acquire", response_model=TaskRead)
async def acquire_track(
    track_tidal_id: int,
    force: bool = False,
):
    task_description = "Acquire Track: " + str(track_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireTrack, description=task_description, track_tidal_id=track_tidal_id, force=force, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task


# Video endpoints
@app.get("/videos", response_model=list[VideoRead])
async def get_videos(offset: int = 0, limit: int = 50):
    with Session(DatabaseAPI().engine) as session:
        videos = session.exec(select(Video).offset(offset).limit(limit)).all()
        return videos

@app.get("/videos/{video_tidal_id}", response_model=VideoRead)
async def get_video(video_tidal_id: int):
    with Session(DatabaseAPI().engine) as session:
        video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id)).one()
        return video

@app.patch("/videos/{video_tidal_id}", response_model=VideoRead)
async def patch_video(video_tidal_id: int, video: VideoUpdate):
    with Session(DatabaseAPI().engine) as session:
        db_video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id)).one_or_none()
        if db_video is None:
            raise HTTPException(404, "Video not found")
        video_data = video.model_dump(exclude_unset=True)
        db_video.sqlmodel_update(video_data)
        session.commit()
        session.refresh(db_video)
        return db_video

@app.get("/videos/{video_tidal_id}/scan", response_model=TaskRead)
async def scan_video(video_tidal_id: int):
    task_description = "Scan Video: " + str(video_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanVideo, description=task_description, video_tidal_id=video_tidal_id, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/videos/{video_tidal_id}/acquire", response_model=TaskRead)
async def acquire_video(
    video_tidal_id: int,
    force: bool = False,
):
    task_description = "Acquire Video: " + str(video_tidal_id)
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireVideo, description=task_description, video_tidal_id=video_tidal_id, force=force, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task


# Other
@app.get("/scrape/monitored", response_model=TaskRead)
async def scrape_monitored():
    task_description = "Scrape All Monitored Artists"
    task_id = TaskHandler().start_task(target=LighthouseAPI().scrapeAllMonitoredArtists, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/scan/content", response_model=TaskRead)
async def scan_content():
    task_description = "Scan All Content"
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanAll, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/scan/tracks", response_model=TaskRead)
async def scan_tracks():
    task_description = "Scan All Tracks"
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanAllTracks, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/scan/videos", response_model=TaskRead)
async def scan_videos():
    task_description = "Scan All Videos"
    task_id = TaskHandler().start_task(target=LighthouseAPI().scanAllVideos, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/acquire/content", response_model=TaskRead)
async def acquire_content():
    task_description = "Acquire All Content"
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireAll, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/acquire/tracks", response_model=TaskRead)
async def acquire_tracks():
    task_description = "Acquire All Tracks"
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireAllTracks, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task

@app.get("/acquire/videos", response_model=TaskRead)
async def acquire_videos():
    task_description = "Acquire All Videos"
    task_id = TaskHandler().start_task(target=LighthouseAPI().acquireAllVideos, description=task_description, endpoint=True)
    with Session(DatabaseAPI().engine) as session:
        task = session.exec(select(Task).where(Task.id == task_id)).one()
    return task
