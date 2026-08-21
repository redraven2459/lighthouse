import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

SystemUiOverlayStyle getBaseSystemUiOverlayStyle(dynamic context) {
  return SystemUiOverlayStyle(
    statusBarIconBrightness: Theme.of(context).brightness == Brightness.light ? Brightness.dark : Brightness.light
  );
}
