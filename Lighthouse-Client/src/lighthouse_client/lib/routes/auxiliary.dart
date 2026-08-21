import 'package:flutter/material.dart';

import 'package:go_router/go_router.dart';

import 'package:lighthouse_client/pages/auxiliary/connect.dart';
import 'package:lighthouse_client/pages/auxiliary/waitingForTidalApiAuth.dart';
import 'package:lighthouse_client/pages/auxiliary/waitingForTidekeeperAuth.dart';
import 'package:lighthouse_client/utils/models.dart';

List<RouteBase> createAuxiliaryRoutes() {
  return <RouteBase>[
    GoRoute(
      path: '/waitingForTidalApiAuth',
      builder: (context, state) {
        final AuthDetails authDetails = state.extra as AuthDetails;
        return WaitingForTidalApiAuthPage(authDetails: authDetails);
      },
    ),
    GoRoute(
      path: '/waitingForTidekeeperAuth',
      builder: (context, state) {
        final AuthDetails authDetails = state.extra as AuthDetails;
        return WaitingForTidekeeperAuthPage(authDetails: authDetails);
      },
    ),
    GoRoute(
      path: '/connect',
      builder: (context, state) => const ConnectPage(),
    ),
  ];
}
