import 'package:flutter/material.dart';
import 'package:flutter_web_plugins/url_strategy.dart';

import 'package:go_router/go_router.dart';

import 'package:lighthouse_client/themes/main_theme.dart';
import 'package:lighthouse_client/routes/core.dart';
import 'package:lighthouse_client/routes/auxiliary.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');

void main() {
  usePathUrlStrategy();
  GoRouter.optionURLReflectsImperativeAPIs = true;
  runApp(const MainApp());
}

class MainApp extends StatefulWidget {
  const MainApp({super.key});

  @override
  State<MainApp> createState() => _MainAppState();
}

class _MainAppState extends State<MainApp> {
  Brightness? brightnessOverride;

  @override
  void initState() {
    super.initState();
    //brightnessOverride = Brightness.light;
    //brightnessOverride = Brightness.dark;
  }

  final _router = GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/connect',
    observers: [routeObserver],
    routes: <RouteBase>[
      ...createAuxiliaryRoutes(),
      createCoreStack(),
    ],
    // TODO: Improve by creating an error builder for 404
  );

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: "Lighthouse",
      debugShowCheckedModeBanner: false,
      theme: ThemeManager.mainTheme(brightness: Brightness.light, brightnessOverride: brightnessOverride),
      darkTheme: ThemeManager.mainTheme(brightness: Brightness.dark, brightnessOverride: brightnessOverride),
      themeMode: ThemeMode.system,
      routerConfig: _router,
    );
  }
}
