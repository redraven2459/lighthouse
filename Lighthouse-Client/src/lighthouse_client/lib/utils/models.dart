class AuthDetails {
  final int taskID;
  final String authAddress;

  AuthDetails({
    required this.taskID,
    required this.authAddress,
  });
}

class RootResponse {
  final SemanticVersionObject apiVersionServer;
  final SemanticVersionObject databaseVersionServer;
  final DateTime timestampServer;

  RootResponse({
    required this.apiVersionServer,
    required this.databaseVersionServer,
    required this.timestampServer,
  });

  factory RootResponse.fromJson(Map<String, dynamic> json) {
    return RootResponse(
      apiVersionServer: SemanticVersionObject.fromString(json["api_version"]),
      databaseVersionServer:SemanticVersionObject.fromString(json["database_version"]),
      timestampServer: DateTime.parse(json["timestamp"]),
    );
  }
}

class SemanticVersionObject {
  int majorVersion;
  int minorVersion;
  int patchVersion;

  SemanticVersionObject({
    required this.majorVersion,
    required this.minorVersion,
    required this.patchVersion,
  });

  String get version => "${majorVersion}.${minorVersion}.${patchVersion}";

  factory SemanticVersionObject.fromString(String string) {
    return SemanticVersionObject(
      majorVersion: int.parse(string.split('.')[0]),
      minorVersion: int.parse(string.split('.')[1]),
      patchVersion: int.parse(string.split('.')[2]),
    );
  }
}

enum TaskStatusCode {
  complete(200),
  accepted(202),
  waitingForTidalApiAuth(801),
  waitingForTidalApiLockBackground(802),
  waitingForTidalApiLockForeground(803),
  waitingForTidekeeperAuth(804),
  waitingForTidekeeperLock(805),
  waitingForDatabaseLock(806),
  interrupted(900);

  final int value;

  const TaskStatusCode(this.value);

  static TaskStatusCode fromValue(int value) {
    return TaskStatusCode.values.firstWhere(
      (status) => status.value == value,
    );
  }
}

enum AcquisitionState {
  pending(-1),
  empty(0),
  acquired(1),
  notFound(404);

  final int value;

  const AcquisitionState(this.value);

  static AcquisitionState fromValue(int value) {
    return AcquisitionState.values.firstWhere(
      (status) => status.value == value,
    );
  }
}

class Task {
  final int id;
  final TaskStatusCode statusCode;
  final String description;
  final String message;
  final Map<String, dynamic> data;
  final List<String> stdout;
  final DateTime createTime;
  final DateTime? completeTime;
  final DateTime expireTime;

  Task({
    required this.id,
    required this.statusCode,
    required this.description,
    required this.message,
    required this.data,
    required this.stdout,
    required this.createTime,
    required this.completeTime,
    required this.expireTime,
  });

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json["id"],
      statusCode: TaskStatusCode.fromValue(json["status_code"]),
      description: json["description"],
      message: json["message"],
      data: Map<String, dynamic>.from(json["data"]),
      stdout: List<String>.from(json["stdout"]),
      createTime: DateTime.parse(json["create_time"]),
      completeTime: json["complete_time"] != null ? DateTime.parse(json["complete_time"]) : null,
      expireTime: DateTime.parse(json["expire_time"])
    );
  }
}

class ArtistInformation {
  final Artist artist;
  final List<AlbumInformation> primaryAlbumsInformation;
  final List<AlbumInformation> secondaryAlbumsInformation;
  final List<Video> primaryVideos;
  final List<Video> secondaryVideos;

  ArtistInformation({
    required this.artist,
    required this.primaryAlbumsInformation,
    required this.secondaryAlbumsInformation,
    required this.primaryVideos,
    required this.secondaryVideos,
  });

  factory ArtistInformation.fromJson(Map<String, dynamic> json) {
    return ArtistInformation(
      artist: Artist.fromJson(json["artist"]),
      primaryAlbumsInformation: (json["primary_albums_information"] as List).map((albumInformation) => AlbumInformation.fromJson(albumInformation)).toList(),
      secondaryAlbumsInformation: (json["secondary_albums_information"] as List).map((albumInformation) => AlbumInformation.fromJson(albumInformation)).toList(),
      primaryVideos: (json["primary_videos"] as List).map((video) => Video.fromJson(video)).toList(),
      secondaryVideos: (json["secondary_videos"] as List).map((video) => Video.fromJson(video)).toList(),
    );
  }
}

class AlbumInformation {
  final Album album;
  final List<Track> tracks;

  AlbumInformation({
    required this.album,
    required this.tracks,
  });

  factory AlbumInformation.fromJson(Map<String, dynamic> json) {
    return AlbumInformation(
      album: Album.fromJson(json["album"]),
      tracks: (json["tracks"] as List).map((track) => Track.fromJson(track)).toList(),
    );
  }
}

class Artist {
  final int id;
  final int tidalID;
  final String name;
  final String? biography;
  final String? imageSourceLocation;
  final String? imageCacheID;
  final bool monitored;
  final DateTime syncTime;
  final DateTime? albumsSyncTime;
  final DateTime? videosSyncTime;
  final DateTime? albumsScanTime;
  final DateTime? videosScanTime;

  Artist({
    required this.id,
    required this.tidalID,
    required this.name,
    required this.biography,
    required this.imageSourceLocation,
    required this.imageCacheID,
    required this.monitored,
    required this.syncTime,
    required this.albumsSyncTime,
    required this.videosSyncTime,
    required this.albumsScanTime,
    required this.videosScanTime,
  });

  factory Artist.fromJson(Map<String, dynamic> json) {
    return Artist(
      id: json["id"],
      tidalID: json["tidal_id"],
      name: json["name"],
      biography: json["biography"],
      imageSourceLocation: json["image_source_location"],
      imageCacheID: json["image_cache_id"],
      monitored: json["monitored"],
      syncTime: DateTime.parse(json["sync_time"]),
      albumsSyncTime: json["albums_sync_time"] != null ? DateTime.parse(json["albums_sync_time"]) : null,
      videosSyncTime: json["videos_sync_time"] != null ? DateTime.parse(json["videos_sync_time"]) : null,
      albumsScanTime: json["albums_scan_time"] != null ? DateTime.parse(json["albums_scan_time"]) : null,
      videosScanTime: json["videos_scan_time"] != null ? DateTime.parse(json["videos_scan_time"]) : null,
    );
  }
}

class Album {
  final int id;
  final int tidalID;
  final String name;
  final int primaryArtistTidalID;
  final String? imageSourceLocation;
  final String? imageCacheID;
  final bool monitored;
  final DateTime syncTime;
  final DateTime? tracksSyncTime;
  final DateTime? tracksScanTime;

  Album ({
    required this.id,
    required this.tidalID,
    required this.name,
    required this.primaryArtistTidalID,
    required this.imageSourceLocation,
    required this.imageCacheID,
    required this.monitored,
    required this.syncTime,
    required this.tracksSyncTime,
    required this.tracksScanTime,
  });

  factory Album.fromJson(Map<String, dynamic> json) {
    return Album(
      id: json["id"],
      tidalID: json["tidal_id"],
      name: json["name"],
      primaryArtistTidalID: json["primary_artist_tidal_id"],
      imageSourceLocation: json["image_source_location"],
      imageCacheID: json["image_cache_id"],
      monitored: json["monitored"],
      syncTime: DateTime.parse(json["sync_time"]),
      tracksSyncTime: json["tracks_sync_time"] != null ? DateTime.parse(json["tracks_sync_time"]) : null,
      tracksScanTime: json["tracks_scan_time"] != null ? DateTime.parse(json["tracks_scan_time"]) : null,
    );
  }
}

class Track {
  final int id;
  final int tidalID;
  final int number;
  final String name;
  final int albumTidalID;
  final AcquisitionState acquisitionState;
  final String? acquisitionQuality;
  final bool monitored;
  final DateTime syncTime;
  final DateTime? scanTime;

  Track ({
    required this.id,
    required this.tidalID,
    required this.number,
    required this.name,
    required this.albumTidalID,
    required this.acquisitionState,
    required this.acquisitionQuality,
    required this.monitored,
    required this.syncTime,
    required this.scanTime,
  });

  factory Track.fromJson(Map<String, dynamic> json) {
    return Track(
      id: json["id"],
      tidalID: json["tidal_id"],
      number: json["number"],
      name: json["name"],
      albumTidalID: json["album_tidal_id"],
      acquisitionState: AcquisitionState.fromValue(json["acquisition_state"]),
      acquisitionQuality: json["acquisition_quality"],
      monitored: json["monitored"],
      syncTime: DateTime.parse(json["sync_time"]),
      scanTime: json["scan_time"] != null ? DateTime.parse(json["scan_time"]) : null,
    );
  }
}

class Video {
  final int id;
  final int tidalID;
  final String name;
  final int primaryArtistTidalID;
  final AcquisitionState acquisitionState;
  final bool monitored;
  final DateTime syncTime;
  final DateTime? scanTime;

  Video ({
    required this.id,
    required this.tidalID,
    required this.name,
    required this.primaryArtistTidalID,
    required this.acquisitionState,
    required this.monitored,
    required this.syncTime,
    required this.scanTime,
  });

  factory Video.fromJson(Map<String, dynamic> json) {
    return Video(
      id: json["id"],
      tidalID: json["tidal_id"],
      name: json["name"],
      primaryArtistTidalID: json["primary_artist_tidal_id"],
      acquisitionState: AcquisitionState.fromValue(json["acquisition_state"]),
      monitored: json["monitored"],
      syncTime: DateTime.parse(json["sync_time"]),
      scanTime: json["scan_time"] != null ? DateTime.parse(json["scan_time"]) : null,
    );
  }
}
