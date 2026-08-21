import 'package:flutter/material.dart';

class SectionDivider extends StatelessWidget {
  const SectionDivider({
    super.key,
    required this.text,
    required this.onExpandToggle,
    required this.expanded,
  });

  final String text;
  final VoidCallback? onExpandToggle;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          icon: expanded ? Icon(Icons.expand_less) : Icon(Icons.expand_more),
          onPressed: onExpandToggle,
        ),
        Text(text),
        SizedBox(width: 10),
        Expanded(child: Divider()),
      ]
    );
  }
}
