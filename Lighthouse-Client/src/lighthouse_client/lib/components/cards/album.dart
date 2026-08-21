import 'package:flutter/material.dart';

import 'package:lighthouse_client/components/row_button.dart';

import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/responsive_utils.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';


class AlbumCard extends StatefulWidget {
  const AlbumCard({
    super.key,
    required this.albumInformation,
    required this.updateCardCallback,
    required this.activeTaskCardCallback,
  });

  final AlbumInformation albumInformation;
  final void Function () updateCardCallback;
  final void Function () activeTaskCardCallback;

  @override
  State<AlbumCard> createState() => _AlbumCardState();
}

class _AlbumCardState extends State<AlbumCard> with AutomaticKeepAliveClientMixin {
  @override
  void initState() {
    super.initState();
  }

  @override
  bool get wantKeepAlive => true;

  bool _expanded = false;

  void _onExpandToggle() {
    _expanded = !_expanded;
    setState((){});
  }

  void toggleMonitored({required BuildContext context}) async {
    await LighthouseServerAPI().patchAlbum(context: context, tidalID: widget.albumInformation.album.tidalID, data: {"monitored": !widget.albumInformation.album.monitored});
    widget.updateCardCallback();
  }

  void onScrapeAlbum({required BuildContext context}) async {
    await LighthouseServerAPI().scrapeAlbum(context: context, tidalID: widget.albumInformation.album.tidalID);
    widget.activeTaskCardCallback();
  }

  void onScanAlbum({required BuildContext context}) async {
    await LighthouseServerAPI().scanAlbum(context: context, tidalID: widget.albumInformation.album.tidalID);
    widget.activeTaskCardCallback();
  }

  void onAcquireAlbum({required BuildContext context}) async {
    await LighthouseServerAPI().acquireAlbum(context: context, tidalID: widget.albumInformation.album.tidalID);
    widget.activeTaskCardCallback();
  }

  @override
  Widget build(BuildContext context) {
    // Keep alive
    super.build(context);

    // albumAcquisitionDetails
    final int albumAcquisitionCurrent = widget.albumInformation.tracks.where((track) => track.acquisitionState == AcquisitionState.acquired).length;
    final int albumAcquisitionTotal = widget.albumInformation.tracks.length;

    final bool allTracks404 = (){
      if (albumAcquisitionTotal == 0) {return false;}
      return widget.albumInformation.tracks.every((track) => track.acquisitionState == AcquisitionState.notFound);
    }();

    final Color albumAcquisitionColour = () {
      if (allTracks404) {return Colors.grey;}
      if (albumAcquisitionTotal == 0) {return Colors.grey;}
      return (albumAcquisitionCurrent < albumAcquisitionTotal) ? Colors.red : Colors.green;
    }();

    final String acquisitionString = () {
      if (allTracks404) {return "404";}
      return "${albumAcquisitionCurrent}/${albumAcquisitionTotal}";
    }();

    // Build the card
    return Card(
      child: Container(
        margin: const EdgeInsets.fromLTRB(0, 10, 10, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                IconButton(
                  icon: _expanded ? Icon(Icons.expand_less) : Icon(Icons.expand_more),
                  onPressed: _onExpandToggle,
                ),

                // Album Details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${widget.albumInformation.album.name}",
                        style: Theme.of(context).textTheme.titleMedium,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),

                      Text("(${widget.albumInformation.album.tidalID})"),
                    ]
                  )
                ),

                Container(
                  margin: const EdgeInsets.fromLTRB(10, 0, 10, 0),
                  padding: const EdgeInsets.fromLTRB(2, 0, 2, 0),
                  decoration: BoxDecoration(
                    color: albumAcquisitionColour.withValues(alpha: 0.7),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(acquisitionString),
                ),

                RowButton(icon: widget.albumInformation.album.monitored ? Icons.bookmark : Icons.bookmark_outline, onTap: (() {toggleMonitored(context: context);})),

                RowButton(icon: Icons.search, onTap: (() {onScrapeAlbum(context: context);})),

                RowButton(icon: Icons.document_scanner, onTap: (() {onScanAlbum(context: context);})),

                RowButton(icon: Icons.cloud_download, onTap: (() {onAcquireAlbum(context: context);})),
              ]
            ),
            // Track content
            // Display info about each track
            if (_expanded) ...[
              ...widget.albumInformation.tracks.map((track) => TrackCard(track: track, updateCardCallback: () {widget.updateCardCallback();}, activeTaskCardCallback: () {widget.updateCardCallback();})).toList(),
            ],
          ],
        )
      )
    );
  }
}


class TrackCard extends StatelessWidget {
  const TrackCard({
    super.key,
    required this.track,
    required this.updateCardCallback,
    required this.activeTaskCardCallback,
  });

  final Track track;
  final void Function () updateCardCallback;
  final void Function () activeTaskCardCallback;

  void toggleMonitored({required BuildContext context}) async {
    await LighthouseServerAPI().patchTrack(context: context, tidalID: track.tidalID, data: {"monitored": !track.monitored});
    updateCardCallback();
  }

  void onScanTrack({required BuildContext context}) async {
    await LighthouseServerAPI().scanTrack(context: context, tidalID: track.tidalID);
    activeTaskCardCallback();
  }

  void onAcquireTrack({required BuildContext context}) async {
    await LighthouseServerAPI().acquireTrack(context: context, tidalID: track.tidalID);
    activeTaskCardCallback();
  }

  @override
  Widget build(BuildContext context) {
    final Color trackAcquisitionColour =  switch (track.acquisitionState) {
      AcquisitionState.empty => Colors.red,
      AcquisitionState.pending => Colors.yellow,
      AcquisitionState.notFound => Colors.grey,
      AcquisitionState.acquired => Colors.green,
    };
    final String trackAcquisitionState = switch (track.acquisitionState) {
      AcquisitionState.empty => "missing",
      AcquisitionState.pending => "pending",
      AcquisitionState.notFound => "404",
      AcquisitionState.acquired => "acquired",
    };

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Container(
          alignment: Alignment.center,
          margin: EdgeInsets.fromLTRB(5, 0, 5, 0),
          width: 20,
          child: Text(track.number.toString())
        ),

        Expanded(
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: "${track.name}",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                TextSpan(
                  text: " - (${track.tidalID})",
                ),
              ],
            //maxLines: 2,
            //overflow: TextOverflow.ellipsis,
            ),
          ),
        ),

        Container(
          margin: const EdgeInsets.fromLTRB(10, 0, 10, 0),
          padding: const EdgeInsets.fromLTRB(3, 1, 3, 1),
          decoration: BoxDecoration(
            color: trackAcquisitionColour.withValues(alpha: 0.7),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(track.acquisitionQuality ?? trackAcquisitionState),
        ),

        RowButton(icon: track.monitored ? Icons.bookmark : Icons.bookmark_outline, onTap: (() {toggleMonitored(context: context);})),

        RowButton(icon: Icons.document_scanner, onTap: (() {onScanTrack(context: context);})),

        RowButton(icon: Icons.cloud_download, onTap: (() {onAcquireTrack(context: context);})),
      ],
    );
  }
}
