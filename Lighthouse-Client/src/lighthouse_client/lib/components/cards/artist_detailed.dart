import 'package:flutter/material.dart';

import 'package:lighthouse_client/components/row_button.dart';

import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';

class ArtistDetailedCard extends StatefulWidget {
  const ArtistDetailedCard({
    super.key,
    required this.artist,
    required this.updateCardCallback,
    required this.activeTaskCardCallback,
  });

  final Artist artist;
  final void Function () updateCardCallback;
  final void Function () activeTaskCardCallback;

  @override
  State<ArtistDetailedCard> createState() => _ArtistDetailedCardState();
}

class _ArtistDetailedCardState extends State<ArtistDetailedCard> {
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

  void toggleMonitored({required BuildContext context}) async {
    await LighthouseServerAPI().patchArtist(context: context, tidalID: widget.artist.tidalID, data: {"monitored": !widget.artist.monitored});
    widget.updateCardCallback();
  }

  void onScrapeArtist({required BuildContext context}) async {
    await LighthouseServerAPI().scrapeArtist(context: context, tidalID: widget.artist.tidalID);
    widget.activeTaskCardCallback();
  }

  void onScanArtist({required BuildContext context}) async {
    await LighthouseServerAPI().scanArtist(context: context, tidalID: widget.artist.tidalID);
    widget.activeTaskCardCallback();
  }

  void onAcquireArtist({required BuildContext context}) async {
    await LighthouseServerAPI().acquireArtist(context: context, tidalID: widget.artist.tidalID);
    widget.activeTaskCardCallback();
  }

  void onScrapeAndAcquireArtist({required BuildContext context}) async {
    await LighthouseServerAPI().scrapeAndAcquireArtist(context: context, tidalID: widget.artist.tidalID);
    widget.activeTaskCardCallback();
  }

  @override
  Widget build(BuildContext context) {
    const double cardHeight = 150;
    // Fix biography from displaying null if it doesnt exist
    final String biography = widget.artist.biography ?? "";
    // Used to give images the decoration
    const double aspectRatio = 1;
    const double imageMargin = 10;
    const double imageDecorationHeight = 5;
    const double imageHeight = cardHeight - (imageMargin*2 + imageDecorationHeight);
    const double imageWidth = imageHeight * aspectRatio;
    // Build the card
    return MouseRegion(
      child: GestureDetector(
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
                        style: Theme.of(context).textTheme.titleLarge,
                      ),

                      Text("(${widget.artist.tidalID})"),

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

                RowButton(icon: widget.artist.monitored ? Icons.bookmark : Icons.bookmark_outline, onTap: (() {toggleMonitored(context: context);})),

                RowButton(icon: Icons.search, onTap: (() {onScrapeArtist(context: context);})),

                RowButton(icon: Icons.document_scanner, onTap: (() {onScanArtist(context: context);})),

                RowButton(icon: Icons.cloud_download, onTap: (() {onAcquireArtist(context: context);})),

                RowButton(icon: Icons.api, onTap: (() {onScrapeAndAcquireArtist(context: context);})),

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
