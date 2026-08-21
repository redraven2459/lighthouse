import 'dart:async';

import 'package:flutter/material.dart';

import 'package:url_launcher/url_launcher.dart';
import 'package:go_router/go_router.dart';

import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

class WaitingForTidalApiAuthPage extends StatefulWidget {
  const WaitingForTidalApiAuthPage({
    super.key,
    required this.authDetails,
  });

  final AuthDetails authDetails;

  @override
  State<WaitingForTidalApiAuthPage> createState() => _WaitingForTidalApiAuthPageState();
}

class _WaitingForTidalApiAuthPageState extends State<WaitingForTidalApiAuthPage> {
  @override
  void initState() {
    super.initState();
    _taskRefreshTimer = Timer.periodic(
      const Duration(seconds: 3),
      (_) => checkAuthComplete(context: context, taskID: widget.authDetails.taskID),
    );
  }

  @override
  void dispose() {
    _taskRefreshTimer?.cancel();
    super.dispose();
  }

  Timer? _taskRefreshTimer;

  Future<void> checkAuthComplete({required BuildContext context, required int taskID}) async {
    if (context.mounted) {
      Task? task = await LighthouseServerAPI().pollTaskForAuth(context: context, id: taskID);
      if (task != null) {
        if (task.statusCode != TaskStatusCode.waitingForTidalApiAuth) {
          GoRouter.of(context).go("/search");
        }
      }
    }
  }

  Future<void> onAuthPressed() async {
    final Uri uri = Uri.parse(widget.authDetails.authAddress);
    if (!await launchUrl(uri)) {
      throw Exception('Could not launch $uri');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: getColorScheme(context).surfaceContainer,
      body: SafeArea(
        child: SizedBox(
          height: double.infinity,
          width: double.infinity,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text("Waiting for Tidal API Auth:"),
              TextButton(child: Text("Authenticate"), onPressed: onAuthPressed),
            ],
          ),
        ),
      )
    );
  }
}
