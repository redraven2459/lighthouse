import 'dart:async';

import 'package:flutter/material.dart';

import 'package:lighthouse_client/routes/core.dart';
import 'package:lighthouse_client/components/cards/task.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/models.dart';

class TasksPage extends StatefulWidget {
  const TasksPage({ super.key });

  @override
  State<TasksPage> createState() => _TasksPageState();
}

class _TasksPageState extends State<TasksPage> {
  @override
  void initState() {
    super.initState();
    // Load Tasks
    loadTasks(context);
    // Periodically load takss
    _tasksRefreshTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => loadTasks(context),
    );
  }

  @override
  void dispose() {
    _tasksRefreshTimer?.cancel();
    super.dispose();
  }

  bool _loading = false;
  Timer? _tasksRefreshTimer;
  List<Task>? tasks = [];

  Future<void> loadTasks(BuildContext context) async {
    // Start the loading icon
    _loading = true;
    setState((){});

    // TODO: This code could be improved by wrapping the LighthouseServerAPI calls in try catch blocks and setting _loading = False if an error occurs / do some better error handling.
    List<Task>? results = await LighthouseServerAPI().getAllTasks(context: context);
    if (results != null) {tasks = results;}
    _loading = false;
    setState((){});
  }

  void updateTask(Task newTask) {
    if (tasks != null) {
      final int index = tasks!.indexWhere((item) => item.id == newTask.id);

      if (index != -1) {
        tasks![index] = newTask;
        setState((){});
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Space
        SizedBox(height: 5),

        // Results
        Expanded(
          child: ListView(
            children: [
              // Task Cards
              ...?tasks?.map((task) => TaskCard(key: ValueKey(task.id), task: task, updateTaskCallback: (newTask) {updateTask(newTask);})).toList(),

              SizedBox(height: 5),

              // TODO: need to add a way to search previous pages

              Visibility(
                visible: _loading,
                child: Center(
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: const CircularProgressIndicator()
                  )
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
