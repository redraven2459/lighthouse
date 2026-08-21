import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lighthouse_client/utils/responsive_utils.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

class ResponsiveScaffold extends StatelessWidget {
  const ResponsiveScaffold({
    super.key,
    required this.navigationShell,
    required this.navBarDestinations,
    required this.navRailDestinations,
  });

  final StatefulNavigationShell navigationShell;
  final List<NavigationDestination> navBarDestinations;
  final List<NavigationRailDestination> navRailDestinations;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final WindowSize windowSize = currentWindowSize(constraints.maxWidth);
        final NavComponent navComponent = recommendedNavComponent(windowSize);
        return Scaffold(
          backgroundColor: getColorScheme(context).surfaceContainer,
          body: SafeArea(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Display navRail where appropriate
                if (navComponent == NavComponent.navRail)
                NavigationRail(
                  selectedIndex: navigationShell.currentIndex,
                  destinations: navRailDestinations,
                  onDestinationSelected: (int index) => navigationShell.goBranch(index, initialLocation: index == navigationShell.currentIndex),
                  backgroundColor: getColorScheme(context).surfaceContainer,
                  groupAlignment: 0,
                ),

                Expanded(
                  child: Container(
                    margin: EdgeInsets.fromLTRB(currentMarginSize(windowSize), 5, currentMarginSize(windowSize), 5),
                    child: Container(
                      padding: EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: getColorScheme(context).surface,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: ResponsiveInformation(windowSize: windowSize, child: navigationShell),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          // Display navBar where appropriate
          bottomNavigationBar: navComponent != NavComponent.navBar ? null :
            NavigationBar(
              selectedIndex: navigationShell.currentIndex,
              destinations: navBarDestinations,
              onDestinationSelected: (int index) => navigationShell.goBranch(index, initialLocation: index == navigationShell.currentIndex),
              backgroundColor: getColorScheme(context).surfaceContainer,
            )
        );
      }
    );
  }
}
