import 'dart:async';
import 'dart:io';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:flutter/material.dart';

import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:lighthouse_client/utils/version.dart';
import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

// TODO: implement a means of checking if LighthouseServer is reachable

class LighthouseServerAPI {
  // Define LighthouseServerAPI as a singleton
  static final LighthouseServerAPI _instance = LighthouseServerAPI._internal();
  factory LighthouseServerAPI() {return _instance;}
  LighthouseServerAPI._internal();

  //static const String _serverAddress = "http://127.0.0.1:8000/";
  static const Duration maxTimeout = Duration(seconds: 10);

  Future<String> getServerAddress() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    return prefs.getString("serverAddress") ?? "";
  }

  void processTaskAuth({required BuildContext context, required Task task}) {
    if (task.statusCode == TaskStatusCode.waitingForTidalApiAuth) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) {
          GoRouter.of(context).go("/waitingForTidalApiAuth", extra: AuthDetails(
            taskID: task.id,
            authAddress: task.data["tidal_api_auth_address"],
          ));
        }
      });
    }
    if (task.statusCode == TaskStatusCode.waitingForTidekeeperAuth) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) {
          GoRouter.of(context).go("/waitingForTidekeeperAuth", extra: AuthDetails(
            taskID: task.id,
            authAddress: task.data["tidekeeper_api_auth_address"],
          ));
        }
      });
    }
    return;
  }

  void processTasksAuth({required BuildContext context, required List<Task> tasks}) {
    for (final Task task in tasks) {
      processTaskAuth(context: context, task: task);
    }
  }

  void processConnectionProblem({required BuildContext context}) async{
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (context.mounted) {GoRouter.of(context).go("/connect");}
    });
  }

  Future<bool> testConnection({required BuildContext context, required Uri uri}) async {
    try {
      final response = await http
        .get(
          uri,
          headers: {"Accept": "application/json"},
        )
        .timeout(maxTimeout);

        if (response.statusCode == 200) {
          final Map<String, dynamic> json = jsonDecode(response.body);
          try {
            final RootResponse rootResponse = RootResponse.fromJson(json);

            bool health = true;
            final DateTime timestamp = DateTime.now().toUtc();
            if (apiVersion.majorVersion != rootResponse.apiVersionServer.majorVersion) {health = false;}
            if (apiVersion.minorVersion > rootResponse.apiVersionServer.minorVersion) {health = false;}

            if (databaseVersion.majorVersion != rootResponse.databaseVersionServer.majorVersion) {health = false;}
            if (databaseVersion.minorVersion > rootResponse.databaseVersionServer.minorVersion) {health = false;}

            if (timestamp.difference(rootResponse.timestampServer).abs() > Duration(seconds: 15)) {health = false;}

            if (health == false) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text("Server Health Error", style: TextStyle(color: getColorScheme(context).onError)),
                  backgroundColor: getColorScheme(context).error,
                ),
              );
            }

            return health;
          } catch (e) {}
        }
        return false;
    } on TimeoutException {
      return false;
    } on HandshakeException {
      return false;
    } on http.ClientException {
      return false;
    }
  }

  Future<http.Response?> getRequest({required BuildContext context, required Uri uri}) async {
    try{
      return await http
      .get(
        uri,
        headers: {"Accept": "application/json"},
      )
      .timeout(maxTimeout);
    } catch(e) {
      processConnectionProblem(context: context);
      return null;
    }
  }

  Future<http.Response?> patchRequest({required BuildContext context, required Uri uri, required Map<String, dynamic> data}) async {
    try{
      return await http
      .patch(
        uri,
        headers: {"Accept": "application/json", "Content-Type": "application/json"},
        body: jsonEncode(data),
      )
      .timeout(maxTimeout);
    } catch(e) {
      processConnectionProblem(context: context);
      return null;
    }
  }

  Future<RootResponse?> getRoot({required BuildContext context}) async {
    final String _serverAddress = await getServerAddress();

    final response = await getRequest(context: context, uri: Uri.parse("${_serverAddress}"));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      return RootResponse.fromJson(json);
    } else {
      throw Exception("Failed to load root response");
    }
  }

  Future<Task?> pollTaskForAuth({required BuildContext context, required int id}) async {
    final String _serverAddress = await getServerAddress();

    final response = await getRequest(context: context, uri: Uri.parse("${_serverAddress}tasks/${id}"));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      return Task.fromJson(json);
    } else {
      throw Exception("Failed to load task");
    }
  }

  // Task functions
  Future<List<Task>?> searchForTask({required BuildContext context, required String description}) async {
    final String _serverAddress = await getServerAddress();
    final response = await getRequest(
      context: context,
      uri: Uri.parse("${_serverAddress}tasks").replace(queryParameters: description != null ? {"description": description} : null)
    );
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final List<dynamic> json = jsonDecode(response.body);
      final List<Task> tasks = json.map((item) => Task.fromJson(item)).toList();
      processTasksAuth(context: context, tasks: tasks);
      return tasks;
    } else {
      throw Exception("Failed to load tasks");
    }
  }

  Future<List<Task>?> getAllTasks({required BuildContext context}) async {
    final String _serverAddress = await getServerAddress();

    final response = await getRequest(context: context, uri: Uri.parse("${_serverAddress}tasks"));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final List<dynamic> json = jsonDecode(response.body);
      final List<Task> tasks = json.map((item) => Task.fromJson(item)).toList();
      processTasksAuth(context: context, tasks: tasks);
      return tasks;
    } else {
      throw Exception("Failed to load tasks");
    }
  }

  Future<Task?> getTask({required BuildContext context, required int id}) async {
    final String _serverAddress = await getServerAddress();

    final response = await getRequest(context: context, uri: Uri.parse("${_serverAddress}tasks/${id}"));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      throw Exception("Failed to load task");
    }
  }

  // Artist functions
  Future<List<Artist>?> getAllArtists({required BuildContext context, bool monitoredOnly = false}) async {
    final String _serverAddress = await getServerAddress();
    bool? monitored = null;
    if (monitoredOnly == true) {monitored = true;}

    final response = await getRequest(
      context: context,
      uri: Uri.parse("${_serverAddress}artists").replace(queryParameters: monitored != null ? {"monitored": monitored.toString()} : null),
    );
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final List<dynamic> json = jsonDecode(response.body);
      return json.map((item) => Artist.fromJson(item)).toList();
    } else {
      throw Exception("Failed to load artists");
    }
  }

  Future<Task?> searchArtists({required BuildContext context, required String searchText}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}search/artists?artist_name=${Uri.encodeComponent(searchText)}";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to intepret search results");
    }
  }

  Future<ArtistInformation?> getArtistInformation({required BuildContext context, required int artistTidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${artistTidalID}/information";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      return ArtistInformation.fromJson(json);
    } else {
      print(response.body);
      throw Exception("Failed to intepret artist information");
    }
  }

  Future<AlbumInformation?> getAlbumInformation({required BuildContext context, required int albumTidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}albums/${albumTidalID}/information";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      return AlbumInformation.fromJson(json);
    } else {
      print(response.body);
      throw Exception("Failed to intepret artist information");
    }
  }

  // Monitor functions
  Future<void> patchArtist({required BuildContext context, required int tidalID, required Map<String, dynamic> data}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}";

    final response = await patchRequest(context: context, uri: Uri.parse(address), data: data);
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      return;
    } else {
      print(response.body);
      throw Exception("Failed to patch artist");
    }
  }

  Future<void> patchAlbum({required BuildContext context, required int tidalID, required Map<String, dynamic> data}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}albums/${tidalID}";

    final response = await patchRequest(context: context, uri: Uri.parse(address), data: data);
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      return;
    } else {
      print(response.body);
      throw Exception("Failed to patch album");
    }
  }

  Future<void> patchTrack({required BuildContext context, required int tidalID, required Map<String, dynamic> data}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}tracks/${tidalID}";

    final response = await patchRequest(context: context, uri: Uri.parse(address), data: data);
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      return;
    } else {
      print(response.body);
      throw Exception("Failed to patch track");
    }
  }

  Future<void> patchVideo({required BuildContext context, required int tidalID, required Map<String, dynamic> data}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}videos/${tidalID}";

    final response = await patchRequest(context: context, uri: Uri.parse(address), data: data);
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      return;
    } else {
      print(response.body);
      throw Exception("Failed to patch video");
    }
  }


  // Scrape functions
  Future<Task?> scrapeAllMonitored({required BuildContext context}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}scrape/monitored";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scrapeAllMonitored");
    }
  }

  Future<Task?> scrapeArtist({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scrape/content";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scrapeArtist");
    }
  }

  Future<Task?> scrapeArtistAlbums({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scrape/albums";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scrapeArtistAlbums");
    }
  }

  Future<Task?> scrapeArtistVideos({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scrape/videos";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scrapeArtistVideos");
    }
  }

  Future<Task?> scrapeAlbum({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}albums/${tidalID}/scrape/tracks";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scrapeAlbum");
    }
  }

  // Scan functions
  Future<Task?> scanAll({required BuildContext context}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}scan/content";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanAll");
    }
  }

  Future<Task?> scanArtist({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scan/content";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanArtist");
    }
  }

  Future<Task?> scanArtistAlbums({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scan/albums";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanArtistAlbums");
    }
  }

  Future<Task?> scanArtistVideos({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scan/videos";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanArtistVideos");
    }
  }

  Future<Task?> scanAlbum({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}albums/${tidalID}/scan/tracks";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanAlbum");
    }
  }

  Future<Task?> scanTrack({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}tracks/${tidalID}/scan";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanTrack");
    }
  }

  Future<Task?> scanVideo({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}videos/${tidalID}/scan";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scanTrack");
    }
  }

  // Acquire functions
  Future<Task?> acquireAll({required BuildContext context, }) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}acquire/content";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireAllMonitored");
    }
  }

  Future<Task?> acquireArtist({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/acquire/content";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireArtist");
    }
  }

  Future<Task?> acquireArtistAlbums({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/acquire/tracks";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireArtistAlbums");
    }
  }

  Future<Task?> acquireArtistVideos({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/acquire/videos";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireArtistVideos");
    }
  }

  Future<Task?> acquireAlbum({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}albums/${tidalID}/acquire/tracks";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireAlbum");
    }
  }

  Future<Task?> acquireTrack({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}tracks/${tidalID}/acquire";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireTrack");
    }
  }

  Future<Task?> acquireVideo({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}videos/${tidalID}/acquire";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start acquireVideo");
    }
  }


  Future<Task?> scrapeAndAcquireArtist({required BuildContext context, required int tidalID}) async {
    final String _serverAddress = await getServerAddress();
    final String address = "${_serverAddress}artists/${tidalID}/scrape_and_acquire/content";

    final response = await getRequest(context: context, uri: Uri.parse(address));
    if (response == null) {return null;}

    if (response.statusCode == 200) {
      final Map<String, dynamic> json = jsonDecode(response.body);
      final Task task = Task.fromJson(json);
      processTaskAuth(context: context, task: task);
      return task;
    } else {
      print(response.body);
      throw Exception("Failed to start scrapeAndAcquireArtist");
    }
  }
}
