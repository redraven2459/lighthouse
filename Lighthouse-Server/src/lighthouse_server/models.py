from datetime import datetime, timedelta, UTC
from enum import IntEnum

from sqlmodel import Field, SQLModel, create_engine, JSON, Column, Relationship, Integer
from sqlalchemy.ext.mutable import MutableList, MutableDict

DATABASE_MAJOR_VERSION = 0
DATABASE_MINOR_VERSION = 1
DATABASE_PATCH_VERSION = 0
DATABASE_VERSION = str(DATABASE_MAJOR_VERSION) + "." + str(DATABASE_MINOR_VERSION) + "." + str(DATABASE_PATCH_VERSION)

class RootRead(SQLModel):
    api_version: str
    database_version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class TaskStatusCode(IntEnum):
    COMPLETE = 200
    ACCEPTED = 202
    WAITING_FOR_TIDAL_API_AUTH = 801
    WAITING_FOR_TIDAL_API_LOCK_BACKGROUND = 802
    WAITING_FOR_TIDAL_API_LOCK_FOREGROUND = 803
    WAITING_FOR_TIDEKEEPER_AUTH = 804
    WAITING_FOR_TIDEKEEPER_LOCK = 805
    WAITING_FOR_DATABASE_LOCK = 806
    INTERRUPTED = 900
    ERROR = 999

class AcquisitionState(IntEnum):
    PENDING = -1
    EMPTY = 0
    ACQUIRED = 1
    NOTFOUND = 404

class TidalType(IntEnum):
    ARTIST = 1
    ALBUM = 2
    TRACK = 3
    VIDEO = 4
    TRACKDL = 5
    VIDEODL = 6

# Define Task
class TaskBase(SQLModel):
    status_code: TaskStatusCode = Field(default=TaskStatusCode.ACCEPTED, sa_column=Column(Integer))
    description: str = ""
    message: str = ""
    data: dict = Field(default_factory=dict, sa_column=Column(MutableDict.as_mutable(JSON)))
    stdout: list[str] = Field(default_factory=list, sa_column=Column(MutableList.as_mutable(JSON)))
    create_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    complete_time: datetime | None = Field(default=None)
    expire_time: datetime = Field(default_factory=lambda: datetime.now(UTC) + timedelta(minutes=30))

class TaskCreate(TaskBase):
    pass

class TaskRead(TaskBase):
    id: int

class Task(TaskBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

# Define JobProcessing table
class JobProcessing(SQLModel, table=True):
    tidal_id: int = Field(primary_key=True)
    tidal_type: int = Field(primary_key=True)

# Define SuportingArtist-Album relationship table
class SupportingArtistAlbumLink(SQLModel, table=True):
    artist_id: int = Field(foreign_key="artist.tidal_id", primary_key=True)
    album_id: int = Field(foreign_key="album.tidal_id", primary_key=True)

# Define SuportingArtist-Album relationship table
class SupportingArtistVideoLink(SQLModel, table=True):
    artist_id: int = Field(foreign_key="artist.tidal_id", primary_key=True)
    video_id: int = Field(foreign_key="video.tidal_id", primary_key=True)


# Define Artist
class ArtistBase(SQLModel):
    tidal_id: int = Field(sa_column=Column("tidal_id", Integer, unique=True, index=True))
    name: str
    biography: str | None = Field(default=None)
    image_source_location: str | None = Field(default=None)
    image_cache_id: str | None = Field(default=None)
    monitored: bool = Field(default=False)
    sync_time: datetime
    albums_sync_time: datetime | None = Field(default=None)
    videos_sync_time: datetime | None = Field(default=None)
    albums_scan_time: datetime | None = Field(default=None)
    videos_scan_time: datetime | None = Field(default=None)

class ArtistCreate(ArtistBase):
    pass

class ArtistUpdate(SQLModel):
    monitored: bool | None = None

class ArtistRead(ArtistBase):
    id: int

class Artist(ArtistBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    primary_albums: list["Album"] = Relationship(back_populates="primary_artist")
    secondary_albums: list["Album"] = Relationship(back_populates="secondary_artists", link_model=SupportingArtistAlbumLink)
    primary_videos: list["Video"] = Relationship(back_populates="primary_artist")
    secondary_videos: list["Video"] = Relationship(back_populates="secondary_artists", link_model=SupportingArtistVideoLink)


# Define Album
class AlbumBase(SQLModel):
    tidal_id: int = Field(sa_column=Column("tidal_id", Integer, unique=True, index=True))
    name: str
    primary_artist_tidal_id: int = Field(foreign_key="artist.tidal_id", index=True)
    image_source_location: str = ""
    image_cache_id: str | None = Field(default=None)
    monitored: bool = Field(default=False)
    sync_time: datetime
    tracks_sync_time: datetime | None = Field(default=None)
    tracks_scan_time: datetime | None = Field(default=None)

class AlbumCreate(AlbumBase):
    pass

class AlbumUpdate(SQLModel):
    monitored: bool | None = None

class AlbumRead(AlbumBase):
    id: int

class Album(AlbumBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    primary_artist: Artist = Relationship(back_populates="primary_albums")
    secondary_artists: list["Artist"] = Relationship(back_populates="secondary_albums", link_model=SupportingArtistAlbumLink)
    tracks: list["Track"] = Relationship(back_populates="album")


# Define Track
class TrackBase(SQLModel):
    tidal_id: int = Field(sa_column=Column("tidal_id", Integer, unique=True, index=True))
    number: int
    volume: int
    name: str
    album_tidal_id: int = Field(foreign_key="album.tidal_id", index=True)
    acquisition_state: AcquisitionState = Field(default=AcquisitionState.EMPTY, sa_column=Column(Integer))
    acquisition_quality: str | None = Field(default=None)
    monitored: bool = Field(default=False)
    sync_time: datetime
    scan_time: datetime | None = Field(default=None)

class TrackCreate(TrackBase):
    pass

class TrackUpdate(SQLModel):
    monitored: bool | None = None

class TrackRead(TrackBase):
    id: int

class Track(TrackBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    album: Album = Relationship(back_populates="tracks")


# Define Video
class VideoBase(SQLModel):
    tidal_id: int = Field(sa_column=Column("tidal_id", Integer, unique=True, index=True))
    name: str
    primary_artist_tidal_id: int = Field(foreign_key="artist.tidal_id", index=True)
    acquisition_state: AcquisitionState = Field(default=AcquisitionState.EMPTY, sa_column=Column(Integer))
    monitored: bool = Field(default=False)
    sync_time: datetime
    scan_time: datetime | None = Field(default=None)

class VideoCreate(VideoBase):
    pass

class VideoRead(VideoBase):
    id: int

class VideoUpdate(SQLModel):
    monitored: bool | None = None

class Video(VideoBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    primary_artist: Artist = Relationship(back_populates="primary_videos")
    secondary_artists: list[Artist] = Relationship(back_populates="secondary_videos", link_model=SupportingArtistVideoLink)

class AlbumInformationResponse(SQLModel):
     album: AlbumRead
     tracks: list[TrackRead]

class ArtistInformationResponse(SQLModel):
     artist: ArtistRead
     primary_albums_information: list[AlbumInformationResponse]
     secondary_albums_information: list[AlbumInformationResponse]
     primary_videos: list[VideoRead]
     secondary_videos: list[VideoRead]
