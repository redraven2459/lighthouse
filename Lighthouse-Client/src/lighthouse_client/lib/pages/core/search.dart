import 'dart:async';

import 'package:flutter/material.dart';

import 'package:go_router/go_router.dart';

import 'package:lighthouse_client/routes/core.dart';
import 'package:lighthouse_client/components/cards/artist.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/models.dart';

class SearchPage extends StatefulWidget {
  const SearchPage({ super.key });

  @override
  State<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends State<SearchPage> with RouteAware {
  @override
  void initState() {
    super.initState();
    loadArtists(context: context, searchText: null);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final route = ModalRoute.of(context);
    if (route != null) {
      routeObserver.subscribe(this, route);
    }
  }

  @override
  void dispose() {
    routeObserver.unsubscribe(this);
    super.dispose();
  }

  @override
  void didPopNext() {
    // Another route was popped.
    // This page is visible again.
    loadArtists(context: context, searchText: lastSearchText);
  }

  Timer? _debounceSearchTimer;
  int _searchTaskID = 0;
  bool _loading = false;
  List<Artist> artists = [];
  bool monitoredOnly = true;
  String? lastSearchText;

  Future<void> loadArtists({required BuildContext context, required String? searchText}) async {
    // Start the loading icon
    lastSearchText = searchText;
    _loading = true;
    if (monitoredOnly == true) {artists.removeWhere((artist) => artist.monitored == false);}
    setState((){});
    // Increment the _searchTaskID and assign this search a searchTaskID
    _searchTaskID = _searchTaskID + 1;
    int searchTaskID = _searchTaskID;

    // If the search is not valid then get the default page, otherwise perform a search
    // TODO: This code could be improved by wrapping the LighthouseServerAPI calls in try catch blocks and setting _loading = False if an error occurs / do some better error handling.
    if (searchText == null) {
      List<Artist>? results = await LighthouseServerAPI().getAllArtists(context: context, monitoredOnly: monitoredOnly);
      // If a new search hasnt been started then display the results
      if (searchTaskID == _searchTaskID) {
        if (results != null) {artists = results;}
        _loading = false;
        setState((){});
      }
    } else {
      // Start the search
      Task? task = await LighthouseServerAPI().searchArtists(context: context, searchText: searchText);
      if (task != null) {
        int task_id = task.id;
        TaskStatusCode task_status = TaskStatusCode.accepted;
        // Until the task completes continously poll the task.
        // TODO: a mechanism for displaying the auth challenge needs to be implemented here
        while (task_status != TaskStatusCode.complete) {
          // Poll the task
          await Future.delayed(Duration(milliseconds: 1000));
          task = await LighthouseServerAPI().getTask(context: context, id: task_id);
          if (task == null) {break; /* if task is null break the loop */}
          if (task != null) {
            task_status = task.statusCode;
            // Map the results to Artists
            List<Artist> results = (task.data["results"] as List).map((item) => Artist.fromJson(item)).toList();
            // If a new search hasnt been started then display the results
            if (searchTaskID == _searchTaskID) {
              artists = results;
              if (monitoredOnly == true) {artists.removeWhere((artist) => artist.monitored == false);}
              setState((){});
            }
          }
        }
      }
      if (searchTaskID == _searchTaskID) {
        _loading = false;
        setState((){});
      }
    }
  }

  void _onSearchChanged({required BuildContext context, required String value}) {
    // If a debounce timer exists cancel it
    _debounceSearchTimer?.cancel();
    // Start a debounce timer
    _debounceSearchTimer = Timer(const Duration(milliseconds: 1000), () {
      // If the search is a valid search then search for it, else display all
      if (value.length > 3) {loadArtists(context: context, searchText: value);}
      else {loadArtists(context: context, searchText: null);}
    });
  }

  void _onMonitoredOnlyPressed({required BuildContext context}) {
    monitoredOnly = !monitoredOnly;
    loadArtists(context: context, searchText: lastSearchText);
  }

  void _onArtistPressed(BuildContext context, int artistID) {
    GoRouter.of(context).push("/search/artists/${artistID}");
  }



  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Search Bar
        Row(
          children: [
            Expanded(
              child: SearchAnchor(
                builder: (BuildContext context, SearchController controller) {
                  return SearchBar(
                    controller: controller,
                    padding: const WidgetStatePropertyAll<EdgeInsets>(
                      EdgeInsets.symmetric(horizontal: 16.0),
                    ),
                    onTap: () {},
                    onChanged: (value) {_onSearchChanged(context: context, value: value);},
                    leading: const Icon(Icons.search),
                  );
                },

                // Suggestions
                // Note: this is never used since the controller is never opened
                suggestionsBuilder: (BuildContext context, SearchController controller) {
                  return List<ListTile>.generate(5, (int index) {
                    final String item = 'item $index';
                    return ListTile(
                      title: Text(item),
                      onTap: () {
                        setState(() {
                          controller.closeView(item);
                        });
                      },
                    );
                  });
                },
              ),
            ),

            IconButton(
                iconSize: 24,
                icon: monitoredOnly ? Icon(Icons.bookmark) : Icon(Icons.bookmark_border),
                onPressed: () {_onMonitoredOnlyPressed(context: context);}
            ),
          ]
      ),

        // Space
        SizedBox(height: 5),

        // Results
        Expanded(
          child: ListView(
            children: [
              ...artists
                .map((artist) => ArtistCard(
                  artist: artist,
                  onPressed: (artistID) {_onArtistPressed(context, artistID);}
                )).toList(),

              SizedBox(height: 5),

              Visibility(
                visible: _loading,
                child: Center(
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: const CircularProgressIndicator()
                  )
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
