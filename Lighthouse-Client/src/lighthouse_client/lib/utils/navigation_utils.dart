import 'package:flutter/material.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

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

class BaseNavigationBar extends StatelessWidget{
  const BaseNavigationBar({
    super.key,
    required this.navDestinations,
    required this.navIndex,
    required this.onNavDestinationSelected,
  });

  final List<NavDestination> navDestinations;
  final int navIndex;
  final void Function(int) onNavDestinationSelected;

  @override
  Widget build(BuildContext context) {
    return NavigationBar(
      selectedIndex: navIndex,
      destinations: navDestinations.map((d) {return NavigationDestination(icon: (d.icon), label: (d.label));}).toList(),
      onDestinationSelected: onNavDestinationSelected,
      backgroundColor: getColorScheme(context).surfaceContainer,
    );
  }
}

class BaseNavigationRail extends StatelessWidget{
  const BaseNavigationRail({
    super.key,
    required this.navDestinations,
    required this.navIndex,
    required this.onNavDestinationSelected,
  });

  final List<NavDestination> navDestinations;
  final int navIndex;
  final void Function(int) onNavDestinationSelected;

  @override
  Widget build(BuildContext context) {
    return NavigationRail(
      selectedIndex: navIndex,
      destinations: navDestinations.map((d) {return NavigationRailDestination(icon: (d.icon), label: Text(d.label));}).toList(),
      onDestinationSelected: onNavDestinationSelected,
      backgroundColor: getColorScheme(context).surfaceContainer,
      groupAlignment: 0,
    );
  }
}
