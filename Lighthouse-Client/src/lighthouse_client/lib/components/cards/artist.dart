import 'dart:async';

import 'package:flutter/material.dart';
import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';
import 'package:lighthouse_client/utils/responsive_utils.dart';

class ArtistCard extends StatefulWidget {
  const ArtistCard({
    super.key,
    required this.artist,
    required this.onPressed,
  });

  final Artist artist;
  final ValueChanged<int> onPressed;

  @override
  State<ArtistCard> createState() => _ArtistCardState();
}

class _ArtistCardState extends State<ArtistCard> {
  @override
  void initState() {
    super.initState();
    loadServerAddress();
  }

  Future<void> loadServerAddress() async {
    serverAddress = await LighthouseServerAPI().getServerAddress();
    setState((){});
  }

  bool hover = false;
  String? serverAddress;

  @override
  Widget build(BuildContext context) {
    final WindowSize windowSize = ResponsiveInformation.of(context).windowSize;
    final bool isCompact = (windowSize == WindowSize.compact);
    final bool isMedium = (windowSize == WindowSize.medium);

    final double cardHeight = isCompact? 120 : isMedium? 150 : 200;
    // Fix biography from displaying null if it doesnt exist
    final String biography = widget.artist.biography ?? "";
    // Used to give images the decoration
    const double aspectRatio = 1;
    const double imageMargin = 10;
    const double imageDecorationHeight = 5;
    final double imageHeight = cardHeight - (imageMargin*2 + imageDecorationHeight);
    final double imageWidth = imageHeight * aspectRatio;

    // Build the card
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => hover = true),
      onExit: (_) => setState(() => hover = false),
      child: GestureDetector(
        onTap: () => widget.onPressed(widget.artist.tidalID),
        child: Card(
          elevation: hover ? 20 : 0,
          child: SizedBox(
            height: cardHeight,
            child: Row(
              //crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Profile Image
                Container(
                  margin: EdgeInsets.all(imageMargin),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Column(
                      children: [
                        if (serverAddress != null)
                          Expanded(child: Image.network("${serverAddress}artists/${widget.artist.tidalID}/image", fit: BoxFit.contain)),
                        Container(
                          width: imageWidth,
                          height: imageDecorationHeight,
                          decoration: BoxDecoration(
                            color: widget.artist.monitored ? Colors.green : Colors.red
                          ),
                        ),
                      ]
                    ),
                  ),
                ),

                // Artist Details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        height: 10
                      ),

                      Text(
                        "${widget.artist.name}",
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: isCompact? 20: 22),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),

                      Text(
                        "(${widget.artist.tidalID})",
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),

                      SizedBox(
                        height: 5
                      ),

                      Text(
                        "${biography}",
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                      ),

                      SizedBox(
                        height: 5
                      ),
                    ]
                  )
                ),

                // margin
                SizedBox(
                  width: 10
                ),
              ]
            )
          )
        )
      )
    );
  }
}
