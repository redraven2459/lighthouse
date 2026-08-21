import 'dart:async';

import 'package:flutter/material.dart';

import 'package:url_launcher/url_launcher.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

class ConnectPage extends StatefulWidget {
  const ConnectPage({
    super.key,
  });

  @override
  State<ConnectPage> createState() => _ConnectPageState();
}

class _ConnectPageState extends State<ConnectPage> {
  @override
  void initState() {
    super.initState();
    attemptAuth(context: context, serverAddress: null);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (context.mounted) {loadLastKnownServerAddress();}
    });
  }

  final TextEditingController controller = TextEditingController();
  bool connectionAttemptUnsuccessful = false;
  bool _loading = false;

  Future<bool> attemptAuth({required BuildContext context, required String? serverAddress}) async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    String string = "";
    if (serverAddress == null) {
      string = prefs.getString("serverAddress") ?? "";
    } else {
      string = serverAddress;
    }

    final Uri? uri = Uri.tryParse(string);

    if (context.mounted && uri != null && uri.host.isEmpty == false) {
      bool connectionValid = await LighthouseServerAPI().testConnection(context: context, uri: uri);

      if (connectionValid) {
        await prefs.setString("serverAddress", string);
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (context.mounted) {
            GoRouter.of(context).go("/search");
          }
        });
        setState((){});
        return true;
      }
    }

    connectionAttemptUnsuccessful = true;
    setState((){});
    return false;
  }

  void onConnectPressed({required BuildContext context}) async {
    _loading = true;
    setState((){});

    String address = controller.text;
    if (address.endsWith("/") == false) {
      address = "${address}/";
    }

    bool success = false;
    success = await attemptAuth(context: context, serverAddress: "${address}");
    if (!success) {
      success = await attemptAuth(context: context, serverAddress: "https://${address}");
    }
    if (!success) {
      success = await attemptAuth(context: context, serverAddress: "http://${address}");
    }

    // If it doesnt work: show a snack bar
    _loading = false;
    setState((){});
    if (!success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Invalid Server Address", style: TextStyle(color: getColorScheme(context).onError)),
          backgroundColor: getColorScheme(context).error,
        ),
      );
    }
  }

  void loadLastKnownServerAddress() async {
    final SharedPreferences prefs = await SharedPreferences.getInstance();
    controller.text = prefs.getString("serverAddress") ?? "";
    setState((){});
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: getColorScheme(context).surfaceContainer,
      body: SafeArea(
        child: SizedBox(
          height: double.infinity,
          width: double.infinity,
          child: Visibility(
            visible: connectionAttemptUnsuccessful,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text("Please Enter Server URL:"),
                Container(
                  padding: EdgeInsets.fromLTRB(30, 10, 30, 10),
                  child: TextField(
                    controller: controller,
                  ),
                ),
                TextButton(child: Text("Connect"), onPressed: () {onConnectPressed(context: context);}),
                Container(height: 10),
                Visibility(
                  visible: _loading,
                  child: CircularProgressIndicator(),
                ),
              ],
            ),
          ),
        ),
      )
    );
  }
}
