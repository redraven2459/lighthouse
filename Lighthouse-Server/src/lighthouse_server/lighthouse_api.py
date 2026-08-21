from datetime import datetime, timedelta, UTC
from contextlib import nullcontext
import json, os, subprocess, uuid
from pathlib import Path
from urllib import parse
from urllib.request import urlretrieve
import threading

from sqlalchemy import func
from sqlmodel import Session, select
from fastapi.encoders import jsonable_encoder

from lighthouse_server.settings import Settings
from lighthouse_server.tasks import TaskHandler, TaskStatusCode
from lighthouse_server.tidal_api import TidalAPI
from lighthouse_server.tidekeeper_api import TidekeeperAPI
from lighthouse_server.models import *
from lighthouse_server.database_api import DatabaseAPI, DatabaseLock

class LighthouseAPI():
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        if hasattr(self, "_initialized"):
                return
        self._initialized = True

        self.settings = Settings()
        self.cache_lock = threading.Lock()
        self.scan_lock = threading.Lock()
        return

    @classmethod
    def reset(cls):
        cls._instance = None

    @staticmethod
    def SanitiseStringForPath(string):
        string = string.replace("/", '')
        string = string.replace(">", '')
        string = string.replace("<", '')
        string = string.replace(":", '')
        string = string.replace("\\", '')
        string = string.replace("|", '')
        string = string.replace("?", '')
        string = string.replace("*", '')
        string = string.replace("'", '')
        string = string.replace('"', '')
        string = string.replace('£', '')
        string = string.replace('!', '')
        string = string.replace('@', '')
        string = string.replace(';', '')
        string = string.replace('.', '')
        string = string.replace(',', '')
        string = string.replace('[', '')
        string = string.replace(']', '')
        string = string.replace('#', '')
        string = string.replace('~', '')
        string = string.replace('%', '')
        string = string.replace('^', '')
        return string

    @staticmethod
    def EnsureDirectoryExists(path):
        try:
            os.mkdir(path)
        except FileExistsError:
            pass
        except PermissionError:
            raise RuntimeError(f"Permission denied: Unable to create '{path}'.")
        except Exception as e:
            raise RuntimeError(f"An error occurred: {e}")

    # Scrape
    def scrapeArtistCore(self, task_id, artist_tidal_id, foreground=False, monitored=False):
        TaskHandler().update_task_stdout(task_id, "Scraping artist(core) via tidal_api (artist: " + str(artist_tidal_id) + ")")
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_DATABASE_LOCK)
        with DatabaseLock(artist_tidal_id, TidalType.ARTIST):
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
            # Check the artist does not exist
            with Session(DatabaseAPI().engine) as session:
                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one_or_none()
            if artist is not None:
                return None

            # Query tidal_api for artist information
            queryString = "artists/" + str(artist_tidal_id) + "?countryCode=" + self.settings.country_code + "&include=profileArt&include=biography"
            if foreground:
                status_code, data = TidalAPI().getQueryForeground(task_id, queryString)
            else:
                status_code, data = TidalAPI().getQueryBackground(task_id, queryString)

            # Create artist
            artistDict = {}
            artistDict["tidal_id"] = artist_tidal_id
            artistDict["name"] = LighthouseAPI.SanitiseStringForPath(data["data"]["attributes"]["name"])
            artistDict["monitored"] = monitored
            artistDict["sync_time"] = datetime.now(UTC)

            artistBiographyCode = None
            artistArtworkCode = None
            try:
                artistBiographyCode = data["data"]["relationships"]["biography"]["data"]["id"]
            except:
                pass
            try:
                artistArtworkCode = data["data"]["relationships"]["profileArt"]["data"][0]["id"]
            except:
                pass

            # Process metadata
            included = data["included"]
            for item in included:
                if item["id"] == artistBiographyCode:
                    pass
                if item["id"] == artistArtworkCode:
                    # Get the image source location
                    artistDict["image_source_location"] = item["attributes"]["files"][0]["href"]
                    # Assign an ID to the image and download it
                    file_extension = "." + artistDict["image_source_location"].rsplit(".", 1)[-1]
                    with self.cache_lock:
                        image_id_claimed = False
                        while image_id_claimed == False:
                            image_id = str(uuid.uuid4()) + file_extension
                            path = self.settings.cache_path + "/" + image_id
                            if Path(path).exists():
                                break
                            urlretrieve(artistDict["image_source_location"], path)
                            artistDict["image_cache_id"] = image_id
                            image_id_claimed = True

            # Create the artist
            with Session(DatabaseAPI().engine) as session:
                db_artist = Artist.model_validate(artistDict)
                session.add(db_artist)
                session.commit()
                session.refresh(db_artist)
        return db_artist

    def scrapeArtistVideos(self, task_id, artist_tidal_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping artist videos via tidal_api (artist: " + str(artist_tidal_id) + ")")
        queryString = "artists/" + str(artist_tidal_id) + "/relationships/videos?countryCode=" + self.settings.country_code + "&include=videos"
        page = 1
        while True:
            TaskHandler().update_task_stdout(task_id, "Scraping page: " + str(page))
            status_code, data = TidalAPI().getQueryBackground(task_id, queryString)
            # Extract video IDs from data
            video_tidal_ids = set()
            for entry in data["data"]:
                if entry["type"] == "videos":
                    video_tidal_ids.add(int(entry["id"]))

            # Filter list of video IDs to only those not currently in the DB
            with Session(DatabaseAPI().engine) as session:
                existing_video_tidal_ids = set(session.exec(select(Video.tidal_id).where(Video.tidal_id.in_(video_tidal_ids))).all())
            missing_video_tidal_ids = [video_tidal_id for video_tidal_id in video_tidal_ids if video_tidal_id not in existing_video_tidal_ids]
            videos_to_scrape_ids = missing_video_tidal_ids


            # Process each video on this page
            videos_to_scrape_length = len(videos_to_scrape_ids)
            for video_tidal_id in videos_to_scrape_ids:
                TaskHandler().update_task_stdout(task_id, "Scraping videos via tidal_api (video: " + str(video_tidal_id) + ")")
                TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_DATABASE_LOCK)
                with DatabaseLock(video_tidal_id, TidalType.VIDEO):
                    TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
                    # Check the track definitvely doesnt existin DB
                    with Session(DatabaseAPI().engine) as session:
                        video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id)).one_or_none()
                        if (video is not None):
                            continue

                    # Check contributing artists
                    artistsQueryString = "videos/" + str(video_tidal_id) + "/relationships/artists?countryCode=" + self.settings.country_code + "&include=artists"
                    artistsStatus_code, artistsData = TidalAPI().getQueryBackground(task_id, artistsQueryString)
                    contributing_artist_tidal_ids = []
                    for entry in artistsData["data"]:
                        contributing_artist_tidal_ids.append(int(entry["id"]))
                    primary_artist_tidal_id = contributing_artist_tidal_ids[0]
                    supporting_artist_tidal_ids = contributing_artist_tidal_ids[1:]

                    # Filter list of artist IDs to only those not currently in the DB
                    with Session(DatabaseAPI().engine) as session:
                        existing_artist_tidal_ids = set(session.exec(select(Artist.tidal_id).where(Artist.tidal_id.in_(contributing_artist_tidal_ids))).all())
                    missing_artist_tidal_ids = [temp_artist_tidal_id for temp_artist_tidal_id in contributing_artist_tidal_ids if temp_artist_tidal_id not in existing_artist_tidal_ids]
                    artists_to_scrape_ids = missing_artist_tidal_ids

                    # Ensure all artists have been scraped
                    for supporting_artist_tidal_id in artists_to_scrape_ids:
                        TaskHandler().update_task_stdout(task_id, "Unrecognised artist contributing to video, scraping...")
                        self.scrapeArtistCore(task_id, supporting_artist_tidal_id)

                    # Set monitored by artist_tidal_id
                    with Session(DatabaseAPI().engine) as session:
                        artist = session.exec(select(Artist).where(Artist.tidal_id == primary_artist_tidal_id)).one()
                    monitored = artist.monitored

                    video_dict = {}
                    for item in data["included"]:
                        if item["id"] == str(video_tidal_id):
                            video_dict["name"] = item["attributes"]["title"]
                            break
                    video_dict["tidal_id"] = video_tidal_id
                    video_dict["primary_artist_tidal_id"] = primary_artist_tidal_id
                    video_dict["monitored"] = monitored
                    video_dict["sync_time"] = datetime.now(UTC)

                    with Session(DatabaseAPI().engine) as session:
                        db_video = Video.model_validate(video_dict)
                        session.add(db_video)
                        session.commit()

                    # Add any supporting artists
                    for supporting_artist_tidal_id in supporting_artist_tidal_ids:
                        item_dict = {
                            "artist_id":supporting_artist_tidal_id,
                            "video_id": video_tidal_id
                        }
                        try:
                            with Session(DatabaseAPI().engine) as session:
                                db_savl = SupportingArtistVideoLink.model_validate(item_dict)
                                session.add(db_savl)
                                session.commit()
                        except:
                            pass
                # breakpoint
                if TaskHandler().stop_event.is_set():
                    return

            # Check for additional pages
            try:
                next_cursor = data["links"]["meta"]["nextCursor"]
            except:
                break

            # Prepare for next page
            queryString = "artists/" + str(artist_tidal_id) + "/relationships/videos?countryCode=" + self.settings.country_code + "&include=videos" + "&page%5Bcursor%5D=" + next_cursor
            page = page + 1

            # breakpoint
            if TaskHandler().stop_event.is_set():
                return

        # Update artists's videos_sync_time
        with Session(DatabaseAPI().engine) as session:
            artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
            artist.videos_sync_time = datetime.now(UTC)
            session.commit()

        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)
        return

    def scrapeAlbumTracks(self, task_id, album_tidal_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping album tracks via tidal_api (album: " + str(album_tidal_id) + ")")

        # Set monitored by album_tidal_id
        with Session(DatabaseAPI().engine) as session:
            album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
        monitored = album.monitored

        queryString = "albums/" + str(album_tidal_id) + "/relationships/items?countryCode=" + self.settings.country_code + "&include=items"
        page = 1
        while True:
            TaskHandler().update_task_stdout(task_id, "Scraping page: " + str(page))
            status_code, data = TidalAPI().getQueryBackground(task_id, queryString)
            # Extract track IDs from data
            track_tidal_ids = set()
            track_tidal_track_numbers = {}
            track_tidal_track_volumes = {}
            for entry in data["data"]:
                if entry["type"] == "tracks":
                    track_tidal_ids.add(int(entry["id"]))
                    track_tidal_track_numbers[int(entry["id"])] = entry["meta"]["trackNumber"]
                    track_tidal_track_volumes[int(entry["id"])] = entry["meta"]["volumeNumber"]

            # Filter list of album IDs to only those not currently in the DB
            with Session(DatabaseAPI().engine) as session:
                existing_track_tidal_ids = set(session.exec(select(Track.tidal_id).where(Track.tidal_id.in_(track_tidal_ids))).all())
            missing_track_tidal_ids = [track_tidal_id for track_tidal_id in track_tidal_ids if track_tidal_id not in existing_track_tidal_ids]
            tracks_to_scrape_ids = missing_track_tidal_ids

            # Process each track on this page
            tracks_to_scrape_length = len(tracks_to_scrape_ids)
            for track_tidal_id in tracks_to_scrape_ids:
                TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_DATABASE_LOCK)
                with DatabaseLock(track_tidal_id, TidalType.TRACK):
                    TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
                    # Check the track definitvely doesnt existin DB
                    with Session(DatabaseAPI().engine) as session:
                        track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one_or_none()
                        if (track is not None):
                            continue

                    track_dict = {}
                    for item in data["included"]:
                        if item["id"] == str(track_tidal_id):
                            track_dict["name"] = item["attributes"]["title"]
                            break

                    track_dict["tidal_id"] = track_tidal_id
                    track_dict["number"] = track_tidal_track_numbers[track_tidal_id]
                    track_dict["volume"] = track_tidal_track_volumes[track_tidal_id]
                    track_dict["album_tidal_id"] = album_tidal_id
                    track_dict["monitored"] = monitored
                    track_dict["sync_time"] = datetime.now(UTC)
                    with Session(DatabaseAPI().engine) as session:
                        db_track = Track.model_validate(track_dict)
                        session.add(db_track)
                        session.commit()

            # Check for additional pages
            try:
                next_cursor = data["links"]["meta"]["nextCursor"]
            except:
                break

            # Prepare for next page
            queryString = "albums/" + str(album_tidal_id) + "/relationships/items?countryCode=" + self.settings.country_code + "&include=items" + "&page%5Bcursor%5D=" + next_cursor
            page = page + 1

            # breakpoint
            if TaskHandler().stop_event.is_set():
                return

        # Update album's tracks_sync_time
        with Session(DatabaseAPI().engine) as session:
            album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
            album.tracks_sync_time = datetime.now(UTC)
            session.commit()

        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)
        return

    def scrapeArtistTracks(self, task_id, artist_tidal_id, include_secondary_albums=True, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping artist tracks via tidal_api (artist: " + str(artist_tidal_id) + ")")
        with Session(DatabaseAPI().engine) as session:
            primary_albums_tidal_ids = session.exec(select(Album.tidal_id).where(Album.primary_artist_tidal_id == artist_tidal_id)).all()

        TaskHandler().update_task_stdout(task_id, "Scraping artist tracks(primary) via tidal_api (artist: " + str(artist_tidal_id) + ")")
        primary_albums_length = len(primary_albums_tidal_ids)
        album_i = 1
        for album_tidal_id in primary_albums_tidal_ids:
            TaskHandler().update_task_stdout(task_id, "Scraping primary album tracks via tidal_api (" + str(album_i) + "/" + str(primary_albums_length) + ")")
            self.scrapeAlbumTracks(task_id, album_tidal_id)
            album_i = album_i + 1
            # breakpoint
            if TaskHandler().stop_event.is_set():
                return

        if include_secondary_albums:
            with Session(DatabaseAPI().engine) as session:
                secondary_albums_tidal_ids = session.exec(select(SupportingArtistAlbumLink.album_id).where(SupportingArtistAlbumLink.artist_id == artist_tidal_id)).all()
            TaskHandler().update_task_stdout(task_id, "Scraping artist tracks(secondary) via tidal_api (artist: " + str(artist_tidal_id) + ")")
            secondary_albums_length = len(secondary_albums_tidal_ids)
            album_i = 1
            for album_tidal_id in secondary_albums_tidal_ids:
                TaskHandler().update_task_stdout(task_id, "Scraping secondary album tracks via tidal_api (" + str(album_i) + "/" + str(secondary_albums_length) + ")")
                self.scrapeAlbumTracks(task_id, album_tidal_id)
                album_i = album_i + 1
                # breakpoint
                if TaskHandler().stop_event.is_set():
                    return
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scrapeArtistAlbums(self, task_id, artist_tidal_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping artist albums via tidal_api (artist: " + str(artist_tidal_id) + ")")
        # Get list of album IDs that are attributed (primary/secondary) for that artist
        queryString = "artists/" + str(artist_tidal_id) + "/relationships/albums?countryCode=" + self.settings.country_code + "&include=albums"
        album_tidal_ids = set()
        page = 1
        while True:
            TaskHandler().update_task_stdout(task_id, "Scraping page: " + str(page))

            status_code, data = TidalAPI().getQueryBackground(task_id, queryString)
            # Extract album IDs from data
            for entry in data["data"]:
                if entry["type"] == "albums":
                    album_tidal_ids.add(int(entry["id"]))
            # Check for additional pages
            try:
                next_cursor = data["links"]["meta"]["nextCursor"]
            except:
                break
            # Prepare for next page
            queryString = "artists/" + str(artist_tidal_id) + "/relationships/albums?countryCode=" + self.settings.country_code + "&include=albums&page%5Bcursor%5D=" + next_cursor
            page = page + 1

        # Check work exists
        if len(album_tidal_ids) == 0:
            return

        # Filter list of album IDs to only those not currently in the DB
        with Session(DatabaseAPI().engine) as session:
            existing_album_tidal_ids = set(session.exec(select(Album.tidal_id).where(Album.tidal_id.in_(album_tidal_ids))).all())
        missing_album_tidal_ids = [album_tidal_id for album_tidal_id in album_tidal_ids if album_tidal_id not in existing_album_tidal_ids]
        albums_to_scrape_ids = missing_album_tidal_ids

        # Scrape each album
        albums_to_scrape_ids_length = len(albums_to_scrape_ids)
        album_i = 1
        for album_tidal_id in albums_to_scrape_ids:
            TaskHandler().update_task_stdout(task_id, "Scraping album via tidal_api (" + str(album_i) + "/" + str(albums_to_scrape_ids_length) + ")")
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_DATABASE_LOCK)
            with DatabaseLock(album_tidal_id, TidalType.ALBUM):
                TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
                # Check the album definitvely doesnt exist
                with Session(DatabaseAPI().engine) as session:
                    album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one_or_none()
                    if album is not None:
                        break
                # Query the api
                queryString = "albums/" + str(album_tidal_id) + "?countryCode=" + self.settings.country_code + "&include=artists&include=coverArt&include=items"
                status_code, data = TidalAPI().getQueryBackground(task_id, queryString)

                # Process album artists
                album_artists = data["data"]["relationships"]["artists"]["data"]
                album_primary_artist = album_artists[0]
                album_primary_artist_tidal_id = int(album_primary_artist["id"])
                album_secondary_artists = album_artists[1:]

                # Scrape any missing artists
                album_artist_tidal_ids = set()
                for artist in album_artists:
                    album_artist_tidal_ids.add(int(artist["id"]))

                with Session(DatabaseAPI().engine) as session:
                    existing_artist_tidal_ids = set(session.exec(select(Artist.tidal_id).where(Artist.tidal_id.in_(album_artist_tidal_ids))).all())
                missing_artist_tidal_ids = [artist_tidal_id for artist_tidal_id in album_artist_tidal_ids if artist_tidal_id not in existing_artist_tidal_ids]

                for artist_tidal_id in missing_artist_tidal_ids:
                    TaskHandler().update_task_stdout(task_id, "Unrecognised artist contributing to album, scraping...")
                    self.scrapeArtistCore(task_id, artist_tidal_id)

                TaskHandler().update_task_stdout(task_id, "Saving album to DB...")

                # Set monitored by album_primary_artist_tidal_id
                with Session(DatabaseAPI().engine) as session:
                    artist = session.exec(select(Artist).where(Artist.tidal_id == album_primary_artist_tidal_id)).one()
                monitored = artist.monitored

                # Process the rest of the album
                album_dict = {}
                album_dict["tidal_id"] = album_tidal_id
                album_dict["name"] = data["data"]["attributes"]["title"]
                album_dict["primary_artist_tidal_id"] = int(album_primary_artist["id"])
                album_dict["monitored"] = monitored
                album_dict["sync_time"] = datetime.now(UTC)
                album_dict["tracks_sync_time"] = datetime.now(UTC)

                # Process albumArtworkCode
                albumArtworkCode = None
                try:
                    albumArtworkCode = data["data"]["relationships"]["coverArt"]["data"][0]["id"]
                except:
                    pass
                for item in data["included"]:
                    if item["id"] == albumArtworkCode:
                        # Get the image source location
                        album_dict["image_source_location"] = item["attributes"]["files"][0]["href"]
                        # Assign an ID to the image and download it
                        file_extension = "." + album_dict["image_source_location"].rsplit(".", 1)[-1]
                        with self.cache_lock:
                            image_id_claimed = False
                            while image_id_claimed == False:
                                image_id = str(uuid.uuid4()) + file_extension
                                path = self.settings.cache_path + "/" + image_id
                                if Path(path).exists():
                                    break
                                urlretrieve(album_dict["image_source_location"], path)
                                album_dict["image_cache_id"] = image_id
                                image_id_claimed = True


                # Create album
                with Session(DatabaseAPI().engine) as session:
                    db_album = Album.model_validate(album_dict)
                    session.add(db_album)
                    session.commit()

                # Create secondary artist links
                for artist in album_secondary_artists:
                    item_dict = {
                        "artist_id": artist["id"],
                        "album_id": album_tidal_id
                    }
                    try:
                        with Session(DatabaseAPI().engine) as session:
                            db_saal = SupportingArtistAlbumLink.model_validate(item_dict)
                            session.add(db_saal)
                            session.commit()
                    except:
                        pass
            album_i = album_i + 1
            # breakpoint
            if TaskHandler().stop_event.is_set():
                return

        # Update artist's albums_sync_time
        with Session(DatabaseAPI().engine) as session:
            artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
            artist.albums_sync_time = datetime.now(UTC)
            session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)
        return

    def scrapeArtistContent(self, task_id, artist_tidal_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping artist(content) via tidal_api (artist: " + str(artist_tidal_id) + ")")
        self.scrapeArtistAlbums(task_id, artist_tidal_id)
        # breakpoint
        if TaskHandler().stop_event.is_set():
            return
        self.scrapeArtistTracks(task_id, artist_tidal_id, include_secondary_albums=True)
        # breakpoint
        if TaskHandler().stop_event.is_set():
            return
        self.scrapeArtistVideos(task_id, artist_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)
        return

    def scrapeArtistAll(self, task_id, artist_tidal_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping artist(all) via tidal_api (artist: " + str(artist_tidal_id) + ")")
        self.scrapeArtistCore(task_id, artist_tidal_id, foreground=False)
        # breakpoint
        if TaskHandler().stop_event.is_set():
            return
        self.scrapeArtistAlbums(task_id, artist_tidal_id)
        # breakpoint
        if TaskHandler().stop_event.is_set():
            return
        self.scrapeArtistTracks(task_id, artist_tidal_id, include_secondary_albums=True)
        # breakpoint
        if TaskHandler().stop_event.is_set():
            return
        self.scrapeArtistVideos(task_id, artist_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)
        return

    def scrapeAllMonitoredArtists(self, task_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scraping all monitored artists")
        with Session(DatabaseAPI().engine) as session:
            artists_to_scrape_ids = session.exec(select(Artist.tidal_id).where(Artist.monitored == True)).all()

        if TaskHandler().stop_event.is_set():
            return

        artists_to_scrape_ids_length = len(artists_to_scrape_ids)
        artist_i = 1
        for artist_tidal_id in artists_to_scrape_ids:
           TaskHandler().update_task_stdout(task_id, "Scraping artist via tidal_api (" + str(artist_i) + "/" + str(artists_to_scrape_ids_length) + ")")
           self.scrapeArtistContent(task_id, artist_tidal_id)
           if TaskHandler().stop_event.is_set():
               return
           artist_i = artist_i + 1

        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)
        return


    # Scan
    def buildFromScan(self, task_id):
        message = "Building from scan"
        TaskHandler().update_task_stdout(task_id, message)
        print(message)
        artist_tidal_ids = set()

        # Get albums artists
        message = "Building from scan: Scanning artists via albums"
        TaskHandler().update_task_stdout(task_id, message)
        print(message)
        albums_path_raw = self.settings.music_path + "/"
        albums_path_path = Path(albums_path_raw)
        albums_folder_names = [p.name for p in albums_path_path.iterdir() if p.is_dir()]
        for folder_name in albums_folder_names:
            artist_tidal_ids.add(int(folder_name.rsplit(" - ", 1)[-1]))

        # Get videos artists
        message = "Building from scan: Scanning artists via videos"
        TaskHandler().update_task_stdout(task_id, message)
        print(message)
        videos_path_raw = self.settings.music_videos_path + "/"
        videos_path_path = Path(videos_path_raw)
        videos_folder_names = [p.name for p in videos_path_path.iterdir() if p.is_dir()]
        for folder_name in videos_folder_names:
            artist_tidal_ids.add(int(folder_name.rsplit(" - ", 1)[-1]))

        # Scrape every artist ID
        message = "Building from scan: Scraping artists via tidal_api"
        TaskHandler().update_task_stdout(task_id, message)
        print(message)
        artist_ids_length = len(artist_tidal_ids)
        artist_i = 1
        for artist_tidal_id in artist_tidal_ids:
            message = "Building from scan: Scraping artists via tidal_api ("+ str(artist_i) + "/" + str(artist_ids_length)+ ")"
            TaskHandler().update_task_stdout(task_id, message)
            print(message)
            self.scrapeArtistAll(task_id, artist_tidal_id, monitored=True)
            artist_i = artist_i + 1

    def scanPath(self, task_id, path_raw, is_item=False, force=False):
        acceptable_track_extensions = {"mp3", "m4a", "aac", "flac"}
        acceptable_video_extensions = {"mp4"}

        if is_item == False:
            path = Path(path_raw)
            files = [str(f) for f in path.rglob("*") if f.is_file()]
            for file_name in files:
                file_extension = file_name.rsplit(".", 1)[-1]
                if (file_extension not in acceptable_track_extensions) and (file_extension not in acceptable_video_extensions):
                    continue

                file_name_no_extension = file_name.rsplit(".", 1)[0]
                parts = file_name_no_extension.split(" - ")

                # Try update the relevant record, if the record does not exist perform a full rebuild
                max_retries = 1
                retry_i = 0
                while retry_i <= max_retries:
                    try:
                        if file_extension in acceptable_track_extensions:
                            quality_string = parts[-1]
                            id_string = parts[-2]
                            id_int = int(id_string)
                            with Session(DatabaseAPI().engine) as session:
                                track = session.exec(select(Track).where(Track.tidal_id == id_int)).one()
                                track.acquisition_state = AcquisitionState.ACQUIRED
                                track.acquisition_quality = quality_string
                                session.commit()
                        if file_extension in acceptable_video_extensions:
                            id_string = parts[-1]
                            id_int = int(id_string)
                            with Session(DatabaseAPI().engine) as session:
                                video = session.exec(select(Video).where(Video.tidal_id == id_int)).one()
                                video.acquisition_state = AcquisitionState.ACQUIRED
                                session.commit()
                        break
                    except:
                        # TODO: this needs to be improved to handle TIDAL deleting content. I.e: can we check if the item exists according to tidal (if yes: perform build from scan, if no: mark it as 403 or something?
                        if retry_i >= max_retries:
                            message = "A fatal error occured. Rebuilding the DB did not enable the previously scanned item to be entered into the DB"
                            TaskHandler().update_task_stdout(task_id, message)
                            print(message)
                            raise RuntimeError(message)

                        message = "A critical error occured. An item was scanned but the relevant DB entries did not exist. A full re-build will be performed... note: this can take multiple hours per artist"
                        TaskHandler().update_task_stdout(task_id, message)
                        print(message)
                        retry_i = retry_i + 1
                        self.buildFromScan(task_id)
                continue
        else:
            path = Path(path_raw.rsplit("/", 1)[0])
            try:
                files = [p.name for p in path.iterdir() if p.is_file()]
            except FileNotFoundError:
                files = []
            path_parts = path_raw.split("/")
            match_string = path_parts[-1]
            matched = False
            for file_name in files:
                file_name_no_extension = file_name.rsplit(".", 1)[0]
                file_extension = file_name.rsplit(".", 1)[-1]
                name_parts = file_name_no_extension.split(" - ")
                if (file_extension not in acceptable_track_extensions) and (file_extension not in acceptable_video_extensions):
                    continue
                if (file_name_no_extension == match_string):
                    matched = True

                    # Try update the relevant record, if the record does not exist perform a full rebuild
                    max_retries = 1
                    retry_i = 0
                    while retry_i <= max_retries:
                        try:
                            if file_extension in acceptable_track_extensions:
                                quality_string = name_parts[-1]
                                id_string = name_parts[-2]
                                id_int = int(id_string)
                                with Session(DatabaseAPI().engine) as session:
                                    track = session.exec(select(Track).where(Track.tidal_id == id_int)).one()
                                    track.acquisition_state = AcquisitionState.ACQUIRED
                                    track.acquisition_quality = quality_string
                                break
                            if file_extension in acceptable_video_extensions:
                                id_string = name_parts[-1]
                                id_int = int(id_string)
                                with Session(DatabaseAPI().engine) as session:
                                    video = session.exec(select(Video).where(Video.tidal_id == id_int)).one()
                                    video.acquisition_state = AcquisitionState.ACQUIRED
                                    session.commit()
                                break
                        except:
                            if retry_i >= max_retries:
                                message = "A fatal error occured. Rebuilding the DB did not enable the previously scanned item to be entered into the DB"
                                TaskHandler().update_task_stdout(task_id, message)
                                print(message)
                                raise RuntimeError(message)

                            message = "A critical error occured. An item was scanned but the relevant DB entries did not exist. A full re-build will be performed..."
                            TaskHandler().update_task_stdout(task_id, message)
                            print(message)
                            retry_i = retry_i + 1
                            self.buildFromScan(task_id)
                    continue

    def getArtistMusicPath(self, artist_tidal_id, artist_name):
        return self.settings.music_path + "/" + self.SanitiseStringForPath(artist_name) + " - " + str(artist_tidal_id) + "/"

    def getArtistVideoPath(self, artist_tidal_id, artist_name):
        return self.settings.music_videos_path + "/" + self.SanitiseStringForPath(artist_name) + " - " + str(artist_tidal_id) + "/"

    def getAlbumPath(self, artist_tidal_id, artist_name, album_tidal_id, album_name):
        return self.getArtistMusicPath(artist_tidal_id, artist_name) + self.SanitiseStringForPath(album_name) + " - " + str(album_tidal_id) + "/"

    def getTrackPath(self, artist_tidal_id, artist_name, album_tidal_id, album_name, track_tidal_id, track_name, track_number):
        return self.getAlbumPath(artist_tidal_id, artist_name, album_tidal_id, album_name) + str(track_number) + " - " + self.SanitiseStringForPath(track_name) + " - " + str(track_tidal_id)

    def getVideoPath(self, artist_tidal_id, artist_name, video_tidal_id, video_name):
        return self.getArtistVideoPath(artist_tidal_id, artist_name) + self.SanitiseStringForPath(video_name) + " - " + str(video_tidal_id)

    def scanTrack(self, task_id, track_tidal_id, endpoint=False):
        with self.scan_lock:
            # Mark as unaqcuired
            with Session(DatabaseAPI().engine) as session:
                track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id, Track.acquisition_state == AcquisitionState.ACQUIRED)).one_or_none()
                if track != None:
                    track.acquisition_state = AcquisitionState.PENDING
                    session.commit()

            # Get info
            with Session(DatabaseAPI().engine) as session:
                track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one()
                track_name = track.name
                track_number = track.number
                album_tidal_id = track.album_tidal_id

                album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
                album_name = album.name
                artist_tidal_id = album.primary_artist_tidal_id

                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                artist_name = artist.name

            scanPath = self.getTrackPath(artist_tidal_id, artist_name, album_tidal_id, album_name, track_tidal_id, track_name, track_number)
            self.scanPath(task_id, scanPath, is_item=True)

            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id, Track.acquisition_state == AcquisitionState.PENDING)).one_or_none()
                if track != None:
                    track.acquisition_state = AcquisitionState.EMPTY
                    track.acquisition_quality = None
                    session.commit()

            # Mark track as scanned
            with Session(DatabaseAPI().engine) as session:
                track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one()
                track.scan_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanVideo(self, task_id, video_tidal_id, endpoint=False):
        with self.scan_lock:
            # Mark as unaqcuired
            with Session(DatabaseAPI().engine) as session:
                video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id, Video.acquisition_state == AcquisitionState.ACQUIRED)).one_or_none()
                if video != None:
                    video.acquisition_state = AcquisitionState.PENDING
                    session.commit()

            # Get info
            with Session(DatabaseAPI().engine) as session:
                video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id)).one()
                video_name = video.name
                artist_tidal_id = video.primary_artist_tidal_id

                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                artist_name = artist.name

            scanPath = self.getVideoPath(artist_tidal_id, artist_name, video_tidal_id, video_name)
            self.scanPath(task_id, scanPath, is_item=True)

            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id, Video.acquisition_state == AcquisitionState.PENDING)).one_or_none()
                if video != None:
                    video.acquisition_state = AcquisitionState.EMPTY
                    session.commit()

            # Mark video as scanned
            with Session(DatabaseAPI().engine) as session:
                video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id)).one()
                video.scan_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanAlbum(self, task_id, album_tidal_id, endpoint=False):
        with self.scan_lock:
            # Mark associated tracks as unacquired
            with Session(DatabaseAPI().engine) as session:
                tracks = session.exec(select(Track).where(Track.album_tidal_id == album_tidal_id, Track.acquisition_state == AcquisitionState.ACQUIRED)).all()
                for track in tracks:
                    track.acquisition_state = AcquisitionState.PENDING
                session.commit()

            # Get info
            with Session(DatabaseAPI().engine) as session:
                album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
                album_name = album.name
                artist_tidal_id = album.primary_artist_tidal_id

                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                artist_name = artist.name

            scanPath = self.getAlbumPath(artist_tidal_id, artist_name, album_tidal_id, album_name)
            self.scanPath(task_id, scanPath)

            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                tracks = session.exec(select(Track).where(Track.album_tidal_id == album_tidal_id, Track.acquisition_state == AcquisitionState.PENDING)).all()
                for track in tracks:
                    track.acquisition_state = AcquisitionState.EMPTY
                    track.acquisition_quality = None
                session.commit()

            # Mark tracks as scanned
            with Session(DatabaseAPI().engine) as session:
                tracks = session.exec(select(Track).where(Track.album_tidal_id == album_tidal_id)).all()
                for track in tracks:
                    track.scan_time = datetime.now(UTC)
                session.commit()

            # Mark album as scanned
            with Session(DatabaseAPI().engine) as session:
                album = session.exec(select(Album).where(Album.tidal_id == album_tidal_id)).one()
                album.tracks_sync_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanArtistAlbums(self, task_id, artist_tidal_id, endpoint=False):
        with self.scan_lock:
            # Mark associated tracks as unacquired
            with Session(DatabaseAPI().engine) as session:
                albums = session.exec(select(Album).where(Album.primary_artist_tidal_id == artist_tidal_id)).all()
                for album in albums:
                    album_tidal_id = album.tidal_id
                    tracks = session.exec(select(Track).where(Track.album_tidal_id == album_tidal_id, Track.acquisition_state == AcquisitionState.ACQUIRED)).all()
                    for track in tracks:
                        track.acquisition_state = AcquisitionState.PENDING
                session.commit()

            # Get info
            with Session(DatabaseAPI().engine) as session:
                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                name = artist.name
            albums_path = self.settings.music_path + "/" + self.SanitiseStringForPath(name) + " - " + str(artist_tidal_id) + "/"
            self.scanPath(task_id, albums_path)

            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                albums = session.exec(select(Album).where(Album.primary_artist_tidal_id == artist_tidal_id)).all()
                for album in albums:
                    album_tidal_id = album.tidal_id
                    tracks = session.exec(select(Track).where(Track.album_tidal_id == album_tidal_id, Track.acquisition_state == AcquisitionState.PENDING)).all()
                    for track in tracks:
                        track.acquisition_state = AcquisitionState.EMPTY
                        track.acquisition_quality = None
                session.commit()

            # Mark tracks as scanned
            with Session(DatabaseAPI().engine) as session:
                albums = session.exec(select(Album).where(Album.primary_artist_tidal_id == artist_tidal_id)).all()
                for album in albums:
                    album_tidal_id = album.tidal_id
                    tracks = session.exec(select(Track).where(Track.album_tidal_id == album_tidal_id)).all()
                    for track in tracks:
                        track.scan_time = datetime.now(UTC)
                session.commit()

            # Mark albums as scanned
            with Session(DatabaseAPI().engine) as session:
                albums = session.exec(select(Album).where(Album.primary_artist_tidal_id == artist_tidal_id)).all()
                for album in albums:
                    album.tracks_sync_time = datetime.now(UTC)
                session.commit()

            # Mark Artist Albums as scanned
            with Session(DatabaseAPI().engine) as session:
                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                artist.albums_scan_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanArtistVideos(self, task_id, artist_tidal_id, endpoint=False):
        with self.scan_lock:
            # Mark associated tracks as unacquired
            with Session(DatabaseAPI().engine) as session:
                videos = session.exec(select(Video).where(Video.primary_artist_tidal_id == artist_tidal_id, Video.acquisition_state == AcquisitionState.ACQUIRED)).all()
                for video in videos:
                    video.acquisition_state = AcquisitionState.PENDING
                session.commit()

            # Get info
            with Session(DatabaseAPI().engine) as session:
                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                name = artist.name
            videos_path = self.settings.music_videos_path + "/" + self.SanitiseStringForPath(name) + " - " + str(artist_tidal_id) + "/"
            self.scanPath(task_id, videos_path)

            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                videos = session.exec(select(Video).where(Video.primary_artist_tidal_id == artist_tidal_id, Video.acquisition_state == AcquisitionState.PENDING)).all()
                for video in videos:
                    video.acquisition_state = AcquisitionState.EMPTY
                session.commit()

            # Mark videos as scanned
            with Session(DatabaseAPI().engine) as session:
                videos = session.exec(select(Video).where(Video.primary_artist_tidal_id == artist_tidal_id)).all()
                for video in videos:
                    video.scan_time = datetime.now(UTC)
                session.commit()

            # Mark Artist Videos as scanned
            with Session(DatabaseAPI().engine) as session:
                artist = session.exec(select(Artist).where(Artist.tidal_id == artist_tidal_id)).one()
                artist.videos_scan_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanArtistAll(self, task_id, artist_tidal_id, endpoint=False):
        self.scanArtistAlbums(task_id, artist_tidal_id)
        self.scanArtistVideos(task_id, artist_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanAllTracks(self, task_id, endpoint=False):
        with self.scan_lock:
            # Mark associated tracks as unacquired
            with Session(DatabaseAPI().engine) as session:
                tracks = session.exec(select(Track).where(Track.acquisition_state == AcquisitionState.ACQUIRED)).all()
                for track in tracks:
                    track.acquisition_state = AcquisitionState.PENDING
                session.commit()
            # Scan
            self.scanPath(task_id, self.settings.music_path + "/")
            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                tracks = session.exec(select(Track).where(Track.acquisition_state == AcquisitionState.PENDING)).all()
                for track in tracks:
                    track.acquisition_state = AcquisitionState.EMPTY
                    track.acquisition_quality = None
                session.commit()
            # Mark tracks as scanned
            with Session(DatabaseAPI().engine) as session:
                tracks = session.exec(select(Track)).all()
                for track in tracks:
                    track.scan_time = datetime.now(UTC)
                session.commit()
            # Mark albums as scanned
            with Session(DatabaseAPI().engine) as session:
                albums = session.exec(select(Album)).all()
                for album in albums:
                    album.tracks_sync_time = datetime.now(UTC)
                session.commit()
            # Mark artist albums as scanned
            with Session(DatabaseAPI().engine) as session:
                artists = session.exec(select(Artist)).all()
                for artist in artists:
                    artist.albums_scan_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)


    def scanAllVideos(self, task_id, endpoint=False):
        with self.scan_lock:
            # Mark associated tracks as unacquired
            with Session(DatabaseAPI().engine) as session:
                videos = session.exec(select(Video).where(Video.acquisition_state == AcquisitionState.ACQUIRED)).all()
                for video in videos:
                    video.acquisition_state = AcquisitionState.PENDING
                session.commit()
            # Scan
            self.scanPath(task_id, self.settings.music_videos_path + "/")
            # Check for leftover items
            with Session(DatabaseAPI().engine) as session:
                videos = session.exec(select(Video).where(Video.acquisition_state == AcquisitionState.PENDING)).all()
                for video in videos:
                    video.acquisition_state = AcquisitionState.EMPTY
                session.commit()
            # Mark videos as scanned
            with Session(DatabaseAPI().engine) as session:
                videos = session.exec(select(Video)).all()
                for video in videos:
                    video.scan_time = datetime.now(UTC)
                session.commit()
            # Mark artist video as scanned
            with Session(DatabaseAPI().engine) as session:
                artists = session.exec(select(Artist)).all()
                for artist in artists:
                    artist.videos_scan_time = datetime.now(UTC)
                session.commit()
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def scanAll(self, task_id, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Scanning all")
        self.scanAllTracks(task_id)
        self.scanAllVideos(task_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def buildFromScanAndRescan(self, task_id):
        self.buildFromScan(self, task_id)
        self.scanAll(task_id)


    # Acquire
    def acquireVideo(self, task_id, video_tidal_id, force=False, scan=True, endpoint=False):
        # TODO: consider changing force to force_reacquisition
        TaskHandler().update_task_stdout(task_id, "Acquiring video via tidekeeper (video: " + str(video_tidal_id) + ")")
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_DATABASE_LOCK)
        with DatabaseLock(video_tidal_id, TidalType.VIDEODL):
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
            # Only acquire videos that havent been acquired unless force is set
            if force == False:
                with Session(DatabaseAPI().engine) as session:
                    video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id, Video.acquisition_state != AcquisitionState.EMPTY)).one_or_none()
                    if video is not None:
                        return
            # Only acquire videos that are monitored
            with Session(DatabaseAPI().engine) as session:
                video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id, Video.monitored == True)).one_or_none()
                if video is None:
                    TaskHandler().update_task_stdout(task_id, "Video skipped: not monitored")
                    return
            TidekeeperAPI().acquireVideo(task_id, video_tidal_id)

            # Check item was found
            found = True
            missing_items = TaskHandler().get_task_data_field(task_id, "not_found_items")
            if missing_items is not None:
                if video_tidal_id in missing_items:
                    found = False
                if found == False:
                    with Session(DatabaseAPI().engine) as session:
                        video = session.exec(select(Video).where(Video.tidal_id == video_tidal_id)).one()
                        video.acquisition_state = AcquisitionState.NOTFOUND
                        session.commit()

            # Scan if required
            if scan and found:
                self.scanVideo(task_id, video_tidal_id)
            # Set task complete if required
            if endpoint:
                TaskHandler().set_task_complete(task_id)
        return

    def acquireTrack(self, task_id, track_tidal_id, force=False, scan=True, endpoint=False):
        # TODO: consider changing force to force_reacquisition
        TaskHandler().update_task_stdout(task_id, "Acquiring track via tidekeeper (track: " + str(track_tidal_id) + ")")
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_DATABASE_LOCK)
        with DatabaseLock(track_tidal_id, TidalType.TRACKDL):
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
            # Only acquire tracks that havent been acquired unless force is set
            if force == False:
                with Session(DatabaseAPI().engine) as session:
                    track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id, Track.acquisition_state != AcquisitionState.EMPTY)).one_or_none()
                    if track is not None:
                        return
            # Only acquire tracks that are monitored
            with Session(DatabaseAPI().engine) as session:
                track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id, Track.monitored == True)).one_or_none()
                if track is None:
                    TaskHandler().update_task_stdout(task_id, "Track skipped: not monitored")
                    return
            TidekeeperAPI().acquireTrack(task_id, track_tidal_id)

            # Check item was found
            found = True
            missing_items = TaskHandler().get_task_data_field(task_id, "not_found_items")
            if missing_items is not None:
                if track_tidal_id in missing_items:
                    found = False
                if found == False:
                    with Session(DatabaseAPI().engine) as session:
                        track = session.exec(select(Track).where(Track.tidal_id == track_tidal_id)).one()
                        track.acquisition_state = AcquisitionState.NOTFOUND
                        session.commit()

            # Scan if required
            if scan and found:
                self.scanTrack(task_id, track_tidal_id)
            # Set task complete if required
            if endpoint:
                TaskHandler().set_task_complete(task_id)
        return

    def acquireArtistVideos(self, task_id, artist_tidal_id, include_secondary_videos=True, force=False, scan=True, endpoint=False):
        # Primary videos
        TaskHandler().update_task_stdout(task_id, "Acquiring artist(primary videos) via tidekeeper (artist: " + str(artist_tidal_id) + ")")
        with Session(DatabaseAPI().engine) as session:
            primary_video_tidal_ids = session.exec(select(Video.tidal_id).where(Video.primary_artist_tidal_id == artist_tidal_id)).all()
        video_ids_length = len(primary_video_tidal_ids)
        video_i = 1
        for video_tidal_id in primary_video_tidal_ids:
            TaskHandler().update_task_stdout(task_id, "Acquiring primary video via tidekeeper (" + str(video_i) + "/" + str(video_ids_length) + ")")
            self.acquireVideo(task_id, video_tidal_id, force=force, scan=False)
            video_i = video_i + 1
            # breakpoint
            if TaskHandler().stop_event.is_set():
                return


        # Secondary videos
        if include_secondary_videos:
            TaskHandler().update_task_stdout(task_id, "Acquiring artist(secondary videos) via tidekeeper (artist: " + str(artist_tidal_id) + ")")
            with Session(DatabaseAPI().engine) as session:
                secondary_video_ids = session.exec(select(SupportingArtistVideoLink.video_id).where(SupportingArtistVideoLink.artist_id == artist_tidal_id)).all()
            video_ids_length = len(secondary_video_ids)
            video_i = 1
            for video_tidal_id in secondary_video_ids:
                TaskHandler().update_task_stdout(task_id, "Acquiring secondary video via tidekeeper (" + str(video_i) + "/" + str(video_ids_length) + ")")
                self.acquireVideo(task_id, video_tidal_id, force=force, scan=False)
                video_i = video_i + 1
                # breakpoint
                if TaskHandler().stop_event.is_set():
                    return

        # Scan if required
        if scan:
            if include_secondary_videos == False:
                self.scanArtistVideos(task_id, artist_tidal_id)
            else:
                self.scanAllVideos(task_id)

        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def acquireAlbumTracks(self, task_id, album_tidal_id, force=False, scan=True, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Acquiring album via tidekeeper (album: " + str(album_tidal_id) + ")")
        with Session(DatabaseAPI().engine) as session:
            track_tidal_ids = session.exec(select(Track.tidal_id).where(Track.album_tidal_id == album_tidal_id)).all()
        track_ids_length = len(track_tidal_ids)
        track_i = 1
        for track_tidal_id in track_tidal_ids:
            TaskHandler().update_task_stdout(task_id, "Acquiring track via tidekeeper (" + str(track_i) + "/" + str(track_ids_length) + ")")
            self.acquireTrack(task_id, track_tidal_id, force=force, scan=False)
            track_i = track_i + 1
            # breakpoint
            if TaskHandler().stop_event.is_set():
                return

        # Scan if required
        if scan:
            self.scanAlbum(task_id, album_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def acquireArtistAlbums(self, task_id, artist_tidal_id, include_secondary_albums=True, force=False, scan=True, endpoint=False):
        # Primary albums
        TaskHandler().update_task_stdout(task_id, "Acquiring artist(primary albums) via tidekeeper (artist: " + str(artist_tidal_id) + ")")
        with Session(DatabaseAPI().engine) as session:
            primary_album_ids = session.exec(select(Album.tidal_id).where(Album.primary_artist_tidal_id == artist_tidal_id)).all()
        primary_album_ids_length = len(primary_album_ids)
        album_i = 1
        for album_id in primary_album_ids:
            TaskHandler().update_task_stdout(task_id, "Acquiring primary album via tidekeeper (" + str(album_i) + "/" + str(primary_album_ids_length) + ")")
            self.acquireAlbumTracks(task_id, album_id, force=force, scan=False)
            album_i = album_i + 1
            # breakpoint
            if TaskHandler().stop_event.is_set():
                return

        if include_secondary_albums:
            # Secondary albums
            TaskHandler().update_task_stdout(task_id, "Acquiring artist(secondary albums) via tidekeeper (artist: " + str(artist_tidal_id) + ")")
            with Session(DatabaseAPI().engine) as session:
                secondary_album_ids = session.exec(select(SupportingArtistAlbumLink.album_id).where(SupportingArtistAlbumLink.artist_id == artist_tidal_id)).all()
            secondary_album_ids_length = len(secondary_album_ids)
            album_i = 1
            for album_id in secondary_album_ids:
                TaskHandler().update_task_stdout(task_id, "Acquiring secondary album via tidekeeper (" + str(album_i) + "/" + str(secondary_album_ids_length) + ")")
                self.acquireAlbumTracks(task_id, album_id, force=force, scan=False)
                album_i = album_i + 1
                # breakpoint
                if TaskHandler().stop_event.is_set():
                    return

        # Scan if required
        if scan:
            if include_secondary_albums == False:
                self.scanArtistAlbums(task_id, artist_tidal_id)
            else:
                self.scanAllTracks(task_id)

        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def acquireArtist(self, task_id, artist_tidal_id, include_secondary_albums=True, include_secondary_videos=True, include_videos=True, force=False, scan=True, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Acquiring artist(albums) via tidekeeper (artist: " + str(artist_tidal_id) + ")")
        self.acquireArtistAlbums(task_id, artist_tidal_id, include_secondary_albums=include_secondary_albums, force=force, scan=False)
        if include_videos:
            TaskHandler().update_task_stdout(task_id, "Acquiring artist(videos) via tidal_api (artist: " + str(artist_tidal_id) + ")")
            self.acquireArtistVideos(task_id, artist_tidal_id, include_secondary_videos=include_secondary_videos, force=force, scan=False)
        # Scan if required
        if scan:
            self.scanArtistAll(task_id, artist_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def acquireAllTracks(self, task_id, force=False, scan=True, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Acquiring tracks via tidekeeper")

        # Acquire all tracks
        with Session(DatabaseAPI().engine) as session:
            track_tidal_ids = session.exec(select(Track.tidal_id)).all()
            track_tidal_ids_length = len(track_tidal_ids)
            track_i = 1
            for track_tidal_id in track_tidal_ids:
                TaskHandler().update_task_stdout(task_id, "Acquiring track via tidekeeper (" + str(track_i) + "/" + str(track_tidal_ids_length) + ")")
                self.acquireTrack(task_id, track_tidal_id, force=force, scan=False)
                track_i = track_i + 1
                # breakpoint
                if TaskHandler().stop_event.is_set():
                    return

        # Scan if required
        if scan:
            self.scanAllTracks(task_id, artist_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def acquireAllVideos(self, task_id, force=False, scan=True, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Acquiring videos via tidekeeper")

        # Acquire all videos
        with Session(DatabaseAPI().engine) as session:
            video_tidal_ids = session.exec(select(Video.tidal_id)).all()
            video_tidal_ids_length = len(video_tidal_ids)
            video_i = 1
            for video_tidal_id in video_tidal_ids:
                TaskHandler().update_task_stdout(task_id, "Acquiring video via tidekeeper (" + str(video_i) + "/" + str(video_tidal_ids_length) + ")")
                self.acquireVideo(task_id, video_tidal_id, force=force, scan=False)
                video_i = video_i + 1
                # breakpoint
                if TaskHandler().stop_event.is_set():
                    return

        # Scan if required
        if scan:
            self.scanAllVideos(task_id, artist_tidal_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    def acquireAll(self, task_id, force=False, scan=True, endpoint=False):
        TaskHandler().update_task_stdout(task_id, "Acquiring al content via tidekeeper")
        self.acquireAllTracks(task_id=task_id, force=force, scan=False)
        self.acquireAllVideos(task_id=task_id, force=force, scan=False)

        # Scan if required
        if scan:
            self.scanAll(task_id)
        # Set task complete if required
        if endpoint:
            TaskHandler().set_task_complete(task_id)

    # Other
    def scrapeAndAcquireArtistContent(self, task_id, artist_tidal_id, force_refresh=False):
        TaskHandler().update_task_stdout(task_id, "Scrape and Acquire artist(content) via tidal_api (artist: " + str(artist_tidal_id) + ")")
        self.scrapeArtistContent(task_id, artist_tidal_id)
        self.acquireArtist(task_id, artist_tidal_id, include_secondary_albums=True)
        TaskHandler().set_task_complete(task_id)


    def searchForArtistAndMetadata(self, task_id, text):
        # Sanitise string for DB and query
        safe_text = self.SanitiseStringForPath(text)
        query_text = parse.quote(text, safe='')

        # Search DB for matches
        TaskHandler().update_task_message(task_id, "Searching DB for: " + str(text))
        TaskHandler().update_task_stdout(task_id, "Querying DB for: " + str(safe_text))
        artists = []
        with Session(DatabaseAPI().engine) as session:
            artists = session.exec(select(Artist).where(func.lower(Artist.name).contains(safe_text.lower()))).all()
        TaskHandler().update_task_data_field(task_id, "results", [jsonable_encoder(artist) for artist in artists])

        # First breakpoint
        if TaskHandler().stop_event.is_set():
            return

        # Search TidalAPI's searchSuggestions for additional matches
        TaskHandler().update_task_message(task_id, "Searching Tidal API for: " + str(text))
        TaskHandler().update_task_stdout(task_id, "Querying searchSuggestions: " + str(text))
        print("Query")
        print(query_text)
        queryString = "searchSuggestions?filter%5Bquery%5D=" + str(query_text) + "&countryCode=" + self.settings.country_code + "&include=directHits&explicitFilter=INCLUDE"
        print(queryString)
        status_code, data = TidalAPI().getQueryForeground(task_id, queryString)
        # Filter results to only include IDs of 'artists', return if no artists exist:
        raw_results = data["included"]
        artist_ids = set()
        for raw_result in raw_results:
            if raw_result["type"] == "artists":
                artist_ids.add(raw_result["id"])
        if len(artist_ids) == 0:
            TaskHandler().set_task_complete(task_id)
            return

        # Further filter results to only include ID's for artists that are not currently in the DB, return if no artists are missing
        with Session(DatabaseAPI().engine) as session:
            existing_artist_ids = set(session.exec(select(Artist.tidal_id).where(Artist.tidal_id.in_(artist_ids))).all())
        missing_artist_ids = set()
        for id in artist_ids:
            if id not in existing_artist_ids:
                missing_artist_ids.add(id)
        if len(missing_artist_ids) == 0:
            TaskHandler().set_task_complete(task_id)
            return

        # Second breakpoint
        if TaskHandler().stop_event.is_set():
            return

        # Query each artist to obtain their metadata
        TaskHandler().update_task_message(task_id, "Searching Tidal API for individual artist information")
        missing_artists_len = len(missing_artist_ids)
        missing_artist_i = 1

        # Loop through the missing_artist_ids and create DB entries for them.
        for artist_id in missing_artist_ids:
            # Update stdout
            TaskHandler().update_task_stdout(task_id, "Processing artist (" + str(missing_artist_i) + " / " + str(missing_artists_len) + ")")
            # Create artist entry
            artist = self.scrapeArtistCore(task_id, artist_id)
            # Process result
            if artist is None:
                TaskHandler().update_task_stdout(task_id, "Artist skipped: already in database")
                break
            artists.append(artist)
            TaskHandler().update_task_data_field(task_id, "results", [jsonable_encoder(artist) for artist in artists])

            # Cleanup
            missing_artist_i = missing_artist_i + 1
            if TaskHandler().stop_event.is_set():
                return

        # Update task
        TaskHandler().update_task_data_field(task_id, "results", [jsonable_encoder(artist) for artist in artists])
        TaskHandler().set_task_complete(task_id)
        return
