import 'dart:async';

import 'package:flutter/material.dart';

import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/version.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({ super.key });

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  @override
  void initState() {
    super.initState();
    loadVersionInfo(context: context);
    _pageRefreshTimer = Timer.periodic(
      const Duration(minutes: 1),
      (_) => loadVersionInfo(context: context),
    );
  }

  @override
  void dispose() {
    _pageRefreshTimer?.cancel();
    super.dispose();
  }

  Timer? _pageRefreshTimer;

  DateTime timestamp = DateTime.now().toUtc();
  SemanticVersionObject? apiVersionServer;
  SemanticVersionObject? databaseVersionServer;
  DateTime? timestampServer;

  void loadVersionInfo({required BuildContext context}) async {
    final RootResponse? rootResponse = await LighthouseServerAPI().getRoot(context: context);
    if (rootResponse == null) {return;}
    apiVersionServer = rootResponse.apiVersionServer;
    databaseVersionServer = rootResponse.databaseVersionServer;
    timestampServer = rootResponse.timestampServer;
    timestamp = DateTime.now().toUtc();
    setState((){});
  }

  void onScrapeAllPressed({required BuildContext context}) async {
    await LighthouseServerAPI().scrapeAllMonitored(context: context);
  }

  void onScanAllPressed({required BuildContext context}) async {
    await LighthouseServerAPI().scanAll(context: context);
  }

  void onAcquireAllPressed({required BuildContext context}) async {
    await LighthouseServerAPI().acquireAll(context: context);
  }


  @override
  Widget build(BuildContext context) {
    final String healthString = (){
      if (apiVersionServer == null || databaseVersionServer == null || timestampServer == null) {
        return "unknown";
      }

      bool health = true;
      if (apiVersion.majorVersion != apiVersionServer!.majorVersion) {health = false;}
      if (apiVersion.minorVersion > apiVersionServer!.minorVersion) {health = false;}

      if (databaseVersion.majorVersion != databaseVersionServer!.majorVersion) {health = false;}
      if (databaseVersion.minorVersion > databaseVersionServer!.minorVersion) {health = false;}

      if (timestamp.difference(timestampServer!).abs() > Duration(seconds: 15)) {health = false;}

      if (health) {return "healthy";}
      return "error";
    }();
    return Column(
      children: [
        Container(
          margin: EdgeInsets.fromLTRB(0, 10, 0, 10),
          child: Text("Lighthouse", style: Theme.of(context).textTheme.titleMedium,),
        ),
        Card(
          child: Container(
            width: double.infinity,
            padding: EdgeInsets.fromLTRB(10, 5, 10, 5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("App info:", style: Theme.of(context).textTheme.titleMedium,),
                Text("App Version: ${appVersion.version}"),
                Text("API Version: ${apiVersion.version}"),
                Text("Database Version: ${databaseVersion.version}"),
                Text("Timestamp: ${timestamp.toString()}"),
                Text(""),
                Text("Server info:", style: Theme.of(context).textTheme.titleMedium,),
                Text("API Version: ${apiVersionServer?.version}"),
                Text("Database Version: ${databaseVersionServer?.version}"),
                Text("Timestamp: ${timestampServer?.toString()}"),
                Text(""),
                Text("Health Info:", style: Theme.of(context).textTheme.titleMedium,),
                Text("State: ${healthString}")
              ],
            ),
          )
        ),
        Card(
          child: Container(
            width: double.infinity,
            padding: EdgeInsets.fromLTRB(10, 5, 10, 5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("System Administration Tasks:"),
                Container(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton(
                      icon: Icon(Icons.search),
                      onPressed: () {onScrapeAllPressed(context: context);},
                    ),
                    Container(width: 10),
                    IconButton(
                      icon: Icon(Icons.document_scanner),
                      onPressed: () {onScanAllPressed(context: context);},
                    ),
                    Container(width: 10),
                    IconButton(
                      icon: Icon(Icons.cloud_download),
                      onPressed: () {onAcquireAllPressed(context: context);},
                    ),
                  ],
                ),
                Container(height: 10),
                Text("Note: the ScrapeAllMonitored and AcquireAll tasks above are long running (i.e: >3 hrs per monitored artist).")
              ],
            ),
          ),
        ),
      ],
    );
  }
}
