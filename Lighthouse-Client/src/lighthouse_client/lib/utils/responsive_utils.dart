import 'package:flutter/material.dart';

// WindowSize
const double sizeCompactMediumTransition = 600;
const double sizeMediumExpandedTransition = 840;
const double sizeExpandedLargeTransition = 1200;
const double sizeLargeExtraLargeTransition = 1600;

bool isSizeCompact(double width) {return (width < sizeCompactMediumTransition);}
bool isSizeMedium(double width) {return (sizeCompactMediumTransition <= width) && (width < sizeMediumExpandedTransition);}
bool isSizeExpanded(double width) {return (sizeMediumExpandedTransition <= width) && (width < sizeExpandedLargeTransition);}
bool isSizeLarge(double width) {return (sizeExpandedLargeTransition <= width) && (width < sizeLargeExtraLargeTransition);}
bool isSizeExtraLarge(double width) {return (sizeLargeExtraLargeTransition <= width);}

enum WindowSize {
  compact, medium, expanded, large, extraLarge;
  const WindowSize();
    bool operator >(WindowSize other) {return index > other.index;}
    bool operator >=(WindowSize other) {return index >= other.index;}
    bool operator <(WindowSize other) {return index < other.index;}
    bool operator <=(WindowSize other) {return index <= other.index;}
}

WindowSize currentWindowSize(double width) {
  if (isSizeCompact(width)) {return WindowSize.compact;}
  if (isSizeMedium(width)) {return WindowSize.medium;}
  if (isSizeExpanded(width)) {return WindowSize.expanded;}
  if (isSizeLarge(width)) {return WindowSize.large;}
  return WindowSize.extraLarge;
}

enum NavComponent {navBar, navRail}
NavComponent recommendedNavComponent(WindowSize windowSize) {
  switch (windowSize) {
    case WindowSize.compact:
      return NavComponent.navBar;
    case WindowSize.medium:
    case WindowSize.expanded:
    case WindowSize.large:
    case WindowSize.extraLarge:
      return NavComponent.navRail;
  }
}

// Margins
const double marginCompact = 16 / 4;
const double marginMedium = 24 / 4;
const double marginExpanded = 24 / 4;
const double marginLarge = 24 / 4;
const double marginExtraLarge = 24 / 4;

double currentMarginSize(WindowSize windowSize) {
  switch (windowSize) {
    case WindowSize.compact:
      return marginCompact;
    case WindowSize.medium:
      return marginMedium;
    case WindowSize.expanded:
      return marginExpanded;
    case WindowSize.large:
      return marginLarge;
    case WindowSize.extraLarge:
      return marginExtraLarge;
  }
}

// Fixed panes
const double widthFixedPaneLarge = 412;
const double widthFixedPaneExtraLarge = 412;

double currentWidthMaxFixedPane(WindowSize windowSize) {
  switch (windowSize) {
    case WindowSize.large:
      return widthFixedPaneLarge;
    case WindowSize.extraLarge:
      return widthFixedPaneExtraLarge;
    default:
      return double.infinity;
  }
}

class ResponsiveInformation extends InheritedWidget {
  const ResponsiveInformation({
    super.key,
    required this.windowSize,
    required super.child,
  });

  final WindowSize windowSize;

  static ResponsiveInformation? maybeOf(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<ResponsiveInformation>();
  }

  static ResponsiveInformation of(BuildContext context) {
    final ResponsiveInformation? result = maybeOf(context);
    assert(result != null, 'No ResponsiveInformation found in context');
    return result!;
  }

  @override
  bool updateShouldNotify(ResponsiveInformation oldWidget) => windowSize != oldWidget.windowSize;
}
