import 'dart:async';
import 'package:flutter/material.dart';

import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/responsive_utils.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

class TaskCard extends StatefulWidget {
  const TaskCard({
    super.key,
    required this.task,
    required this.updateTaskCallback,
  });

  final Task task;
  final void Function (Task newTask) updateTaskCallback;

  @override
  State<TaskCard> createState() => _TaskCardState();
}

class _TaskCardState extends State<TaskCard> with AutomaticKeepAliveClientMixin {
  @override
  void initState() {
    super.initState();
    _scrollToBottomStdout();
  }

  @override
  bool get wantKeepAlive => true;

  @override
  void dispose() {
    _scrollController.dispose();
    _pollTimer?.cancel();
    super.dispose();
  }

  Timer? _pollTimer;

  bool hover = false;
  bool _expanded = false;

  final ScrollController _scrollController = ScrollController();



  void _onExpandToggle({required BuildContext context}) {
    _expanded = !_expanded;
    setState((){});
    if (_expanded) {
      // Start the poll timer
      _pollTimer = Timer.periodic(
        const Duration(seconds: 5),
        (_) => pollTask(context: context),
      );
      // Scroll to bottom of stdout
      _scrollToBottomStdout();
    } else {
      _pollTimer?.cancel();
    }
    if (_expanded) {_scrollToBottomStdout();}
  }

  void pollTask({required BuildContext context}) async {
    if (_expanded) {
      if (![TaskStatusCode.complete, TaskStatusCode.interrupted].contains(widget.task.statusCode)) {
        Task? polledTask = await LighthouseServerAPI().getTask(context: context, id: widget.task.id);
        if (polledTask != null) {
          widget.updateTaskCallback(polledTask);
          _scrollToBottomStdout();
        }
      }
    }
  }

  void _scrollToBottomStdout() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    });
  }

  @override
  Widget build(BuildContext context) {
    final WindowSize windowSize = ResponsiveInformation.of(context).windowSize;
    final bool isCompact = (windowSize == WindowSize.compact);
    final bool isMedium = (windowSize == WindowSize.medium);

    final Color taskStatusCodeColor = switch (widget.task.statusCode) {
      TaskStatusCode.complete => Colors.blue,
      TaskStatusCode.accepted => Colors.green,
      TaskStatusCode.interrupted => Colors.red,
      TaskStatusCode.waitingForTidalApiAuth => Colors.orange,
      TaskStatusCode.waitingForTidekeeperAuth => Colors.orange,
      _=> Colors.yellow,
    };

    final Color stdoutFillColor = getColorScheme(context).secondaryContainer;
    final Color stdoutTextColor = getColorScheme(context).onSecondaryContainer;
    final String stdout = widget.task.stdout.map((item) => item.endsWith("\n") ? item.substring(0, item.length -1) : item).join("\n");

    // Build the card
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => hover = true),
      onExit: (_) => setState(() => hover = false),
      child: Card(
        elevation: hover ? 20 : 0,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                IconButton(
                  icon: _expanded ? Icon(Icons.expand_less) : Icon(Icons.expand_more),
                  onPressed: () {_onExpandToggle(context: context);},
                ),

                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      //SizedBox(
                      //  height: 10
                      //),

                      Text(
                        "${widget.task.description}",
                        style: Theme.of(context).textTheme.titleMedium,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),

                      Text(
                        "(${widget.task.id})",
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ]
                  )
                ),

                Container(
                  margin: const EdgeInsets.fromLTRB(10, 0, 10, 0),
                  padding: const EdgeInsets.fromLTRB(2, 0, 2, 0),
                  decoration: BoxDecoration(
                    color: taskStatusCodeColor.withValues(alpha: 0.7),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text("${widget.task.statusCode.name}"),
                ),
              ],
            ),

            // Expanded
            if (_expanded)
              Container(
                padding: EdgeInsets.fromLTRB(10, 10, 10, 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Message: ${widget.task.message}"),
                    Text("Stdout: "),
                    Container(
                      width: double.infinity,
                      height: 200,
                      margin: EdgeInsets.fromLTRB(0, 3, 0, 3),
                      padding: const EdgeInsets.fromLTRB(5, 2, 5, 2),
                      decoration: BoxDecoration(
                        color: stdoutFillColor,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: ListView(
                        controller: _scrollController,
                        children: widget.task.stdout.map((item) {return Text(item.trimRight(), style: TextStyle(color: stdoutTextColor));}).toList(),
                      ),
                    ),
                  ]
                ),
              ),
          ]
        )
      )
    );
  }
}
