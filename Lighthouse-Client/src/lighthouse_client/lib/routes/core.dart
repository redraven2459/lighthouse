import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:go_router/go_router.dart';

import 'package:lighthouse_client/components/responsive_scaffold.dart';
import 'package:lighthouse_client/pages/empty.dart';
import 'package:lighthouse_client/pages/artist.dart';
import 'package:lighthouse_client/pages/search.dart';
import 'package:lighthouse_client/pages/settings.dart';
import 'package:lighthouse_client/pages/tasks.dart';
import 'package:lighthouse_client/utils/system_ui_utils.dart';

class NavDestination {
  const NavDestination ({
    required this.icon,
    required this.label,
  });

  final Icon icon;
  final String label;
}

const List<NavDestination> navDestinations = [
  NavDestination(
    icon: Icon(Icons.search),
    label: "Search"
  ),
  NavDestination(
    icon: Icon(Icons.dashboard),
    label: "Tasks"
  ),
  NavDestination(
    icon: Icon(Icons.settings),
    label: "Settings"
  ),
];

final RouteObserver<ModalRoute<dynamic>> routeObserver = RouteObserver<ModalRoute<void>>();

StatefulShellRoute createCoreStack() {
  // Convert NavigationDestinations
  final List<NavigationDestination> navBarDestinations = navDestinations.map((d) {return NavigationDestination(icon: (d.icon), label: (d.label));}).toList();
  final List<NavigationRailDestination> navRailDestinations = navDestinations.map((d) {return NavigationRailDestination(icon: (d.icon), label: Text(d.label));}).toList();
  // Create the core stack
  return StatefulShellRoute.indexedStack(
    builder: (BuildContext context, GoRouterState state, StatefulNavigationShell navigationShell) {
      SystemChrome.setSystemUIOverlayStyle(getBaseSystemUiOverlayStyle(context));
      return ResponsiveScaffold(
        navigationShell: navigationShell,
        navBarDestinations: navBarDestinations,
        navRailDestinations: navRailDestinations,
      );
    },
    branches: <StatefulShellBranch>[
      createSearchBranch(),
      createTasksBranch(),
      createSettingsBranch(),
    ],
  );
}

StatefulShellBranch createSearchBranch() {
  return StatefulShellBranch(
    routes: <RouteBase>[
      GoRoute(
        path: '/search',
        builder: (BuildContext context, GoRouterState state) => const SearchPage(),
        // Add route for artist pages
        routes: <RouteBase>[
          GoRoute(
            path: 'artists/:id',
            builder: (BuildContext context, GoRouterState state) {
              final id = int.tryParse(state.pathParameters["id"] ?? "A");
              if (id == null) {return const EmptyPage();}
              return ArtistPage(artistTidalID: id);
            },
          ),
        ],
      ),
    ],
  );
}

StatefulShellBranch createTasksBranch() {
  return StatefulShellBranch(
    routes: <RouteBase>[
      GoRoute(
        path: '/tasks',
        builder: (BuildContext context, GoRouterState state) => const TasksPage(),
        // Add route for artist pages
        routes: <RouteBase>[
          GoRoute(
            path: ':id',
            builder: (BuildContext context, GoRouterState state) => const EmptyPage(),
          ),
        ],
      ),
    ],
  );
}

StatefulShellBranch createSettingsBranch() {
  return StatefulShellBranch(
    routes: <RouteBase>[
      GoRoute(
        path: '/settings',
        builder: (BuildContext context, GoRouterState state) => const SettingsPage(),
      ),
    ],
  );
}
