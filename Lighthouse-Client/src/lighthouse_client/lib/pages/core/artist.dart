import 'dart:async';

import 'package:flutter/material.dart';

import 'package:go_router/go_router.dart';

import 'package:lighthouse_client/components/section_divider.dart';
import 'package:lighthouse_client/components/cards/artist_detailed.dart';
import 'package:lighthouse_client/components/cards/album.dart';
import 'package:lighthouse_client/components/cards/videos.dart';
import 'package:lighthouse_client/components/cards/task.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/models.dart';

class ArtistPage extends StatefulWidget {
  const ArtistPage({
    super.key,
    required this.artistTidalID,
  });

  final int artistTidalID;

  @override
  State<ArtistPage> createState() => _ArtistPageState();
}

class _ArtistPageState extends State<ArtistPage> {
  @override
  void initState() {
    super.initState();
    loadArtistAndTasks(context);
    _pageRefreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => loadArtistAndTasks(context),
    );
  }

  @override
  void dispose() {
    _pageRefreshTimer?.cancel();
    super.dispose();
  }

  // TODO: implement mechanism for loading artist / tasks once a minute

  Timer? _pageRefreshTimer;
  bool _loading = true;
  bool _loadingInitial = true;
  bool _primaryAlbumsExpanded = false;
  bool _secondaryAlbumsExpanded = false;
  bool _videosExpanded = false;
  bool _tasksExpanded = false;

  Artist? artist = null;
  List<AlbumInformation>? primaryAlbumsInformation = null;
  List<AlbumInformation>? secondaryAlbumsInformation = null;
  List<Video>? primaryVideos = null;
  List<Video>? secondaryVideos = null;
  List<Task>? recentTasks = null;

  void loadArtistAndTasks(BuildContext context) {
    loadArtist(context);
    loadTasks(context);
  }

  Future<void> loadArtist(BuildContext context) async {
    // Start the loading icon
    if (_loadingInitial) {_loading = true;}
    setState((){});

    // TODO: This code could be improved by wrapping the LighthouseServerAPI calls in try catch blocks and setting _loading = False if an error occurs / do some better error handling.
    final ArtistInformation? artistInformation = await LighthouseServerAPI().getArtistInformation(context: context, artistTidalID: widget.artistTidalID);
    if (artistInformation != null) {
      artist = artistInformation.artist;
      primaryAlbumsInformation = artistInformation.primaryAlbumsInformation;
      secondaryAlbumsInformation = artistInformation.secondaryAlbumsInformation;
      primaryVideos = artistInformation.primaryVideos;
      secondaryVideos = artistInformation.secondaryVideos;
    }

    // Finish the loading icon
    if (_loadingInitial) {_loading = false;}
    _loadingInitial = false;
    setState((){});
  }

  void onSectionExpandToggle(int section) {
    if (section == 1) {_primaryAlbumsExpanded = !_primaryAlbumsExpanded;}
    if (section == 2) {_secondaryAlbumsExpanded = !_secondaryAlbumsExpanded;}
    if (section == 3) {_videosExpanded = !_videosExpanded;}
    if (section == 4) {_tasksExpanded = !_tasksExpanded;}
    setState((){});
  }

  Future<void> loadTasks(BuildContext context) async {
    // TODO: This code could be improved by wrapping the LighthouseServerAPI calls in try catch blocks and setting _loading = False if an error occurs / do some better error handling.
    List<Task>? results = await LighthouseServerAPI().getAllTasks(context: context);
    if (results != null) {
      final List<int> associatedTidalIDs = [
        ?artist?.tidalID,
        ...?primaryAlbumsInformation?.map((albumInformation) => albumInformation.album.tidalID).toList(),
        ...?secondaryAlbumsInformation?.map((albumInformation) => albumInformation.album.tidalID).toList(),
        ...?primaryVideos?.map((video) => video.tidalID).toList(),
        ...?secondaryVideos?.map((video) => video.tidalID).toList(),
        // Any primary tracks
        ...?primaryAlbumsInformation?.expand((albumInformation) => albumInformation.tracks).map((track) => track.tidalID).toList(),
        // Any secondary tracks
        ...?secondaryAlbumsInformation?.expand((albumInformation) => albumInformation.tracks).map((track) => track.tidalID).toList(),
      ];

      // Keep any task that has a tidalID that matches a tidalID in associatedTidalIDs
      recentTasks = results.where((task) {
        if (associatedTidalIDs.any((tidalID) => task.description.endsWith(" ${tidalID}"))) {return true;}
        return false;
      }).toList();
    }
    setState((){});
  }

  void updateTaskCallback(Task newTask) {
    if (recentTasks != null) {
      final int index = recentTasks!.indexWhere((item) => item.id == newTask.id);

      if (index != -1) {
        recentTasks![index] = newTask;
        setState((){});
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        if (_loading == false) ...[
          ArtistDetailedCard(artist: artist!, updateCardCallback: () {loadArtist(context);},   activeTaskCardCallback: () {loadArtistAndTasks(context);},),
          SectionDivider(text: "Primary Albums", onExpandToggle: (() {onSectionExpandToggle(1);}), expanded: _primaryAlbumsExpanded),
          if (_primaryAlbumsExpanded)
            ...?primaryAlbumsInformation
              ?.map((albumInformation) => AlbumCard(
                albumInformation: albumInformation,
                updateCardCallback: () {loadArtist(context);},
                activeTaskCardCallback: () {loadArtistAndTasks(context);},
              )).toList(),
          SectionDivider(text: "Secondary Albums", onExpandToggle: (() {onSectionExpandToggle(2);}), expanded: _secondaryAlbumsExpanded),
          if (_secondaryAlbumsExpanded)
            ...?secondaryAlbumsInformation
              ?.map((albumInformation) => AlbumCard(
                albumInformation: albumInformation,
                updateCardCallback: () {loadArtist(context);},
                activeTaskCardCallback: () {loadArtistAndTasks(context);},
              )).toList(),
          SectionDivider(text: "Videos", onExpandToggle: (() {onSectionExpandToggle(3);}), expanded: _videosExpanded),
          if (_videosExpanded && primaryVideos != null)
            VideosCard(
              label: "Primary Videos",
              videos: primaryVideos!,
              updateCardCallback: () {loadArtist(context);},
              activeTaskCardCallback: () {loadArtistAndTasks(context);},
            ),
          if (_videosExpanded && secondaryVideos != null)
            VideosCard(
              label: "Secondary Videos",
              videos: secondaryVideos!,
              updateCardCallback: () {loadArtist(context);},
              activeTaskCardCallback: () {loadArtistAndTasks(context);},
            ),
          SectionDivider(text: "Recent Tasks", onExpandToggle: (() {onSectionExpandToggle(4);}), expanded: _tasksExpanded),
          if (_tasksExpanded)
            ...?recentTasks?.map((task) => TaskCard(key: ValueKey(task.id), task: task, updateTaskCallback: updateTaskCallback)).toList()
        ],
      ]
    );
  }
}
