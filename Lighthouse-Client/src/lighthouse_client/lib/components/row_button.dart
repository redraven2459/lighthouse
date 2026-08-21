import 'package:flutter/material.dart';
import 'package:lighthouse_client/utils/color_utils.dart';

class RowButton extends StatelessWidget {
  const RowButton({
    super.key,
    required this.icon,
    required this.onTap,
  });

  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(20),
      onTap: onTap,
      child: Padding(
        padding: EdgeInsets.all(3),
        child: Icon(icon, color: getColorScheme(context).onSurfaceVariant),
      ),
    );
  }
}
