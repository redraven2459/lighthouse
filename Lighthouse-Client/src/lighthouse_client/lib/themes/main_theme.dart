import 'package:flutter/material.dart';

class ThemeManager {
  static ThemeData mainTheme({required Brightness brightness, Brightness? brightnessOverride}) {
    return ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: Colors.greenAccent,
        //seedColor: Colors.blue,
        // brightness: brightness
        brightness: brightnessOverride ?? brightness,
      )
    );
  }
}
