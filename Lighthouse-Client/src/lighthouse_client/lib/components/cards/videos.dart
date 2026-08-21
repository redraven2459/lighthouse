import 'package:flutter/material.dart';

import 'package:lighthouse_client/components/row_button.dart';

import 'package:lighthouse_client/utils/models.dart';
import 'package:lighthouse_client/utils/responsive_utils.dart';
import 'package:lighthouse_client/utils/lighthouse_server_api.dart';


class VideosCard extends StatefulWidget {
  const VideosCard({
    super.key,
    required this.label,
    required this.videos,
    required this.updateCardCallback,
    required this.activeTaskCardCallback,
  });

  final String label;
  final List<Video> videos;
  final void Function () updateCardCallback;
  final void Function () activeTaskCardCallback;

  @override
  State<VideosCard> createState() => _VideosCardState();
}

class _VideosCardState extends State<VideosCard> with AutomaticKeepAliveClientMixin {
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

  @override
  Widget build(BuildContext context) {
    // Keep alive
    super.build(context);

    // albumAcquisitionDetails
    final int acquisitionCurrent = widget.videos.where((video) => video.acquisitionState == AcquisitionState.acquired).length;
    final int acquisitionTotal = widget.videos.length;

    final bool allVideos404 = (){
      if (acquisitionTotal == 0) {return false;}
      return widget.videos.every((video) => video.acquisitionState == AcquisitionState.notFound);
    }();

    final Color acquisitionColour = () {
      if (allVideos404) {return Colors.grey;}
      if (acquisitionTotal == 0) {return Colors.grey;}
      return (acquisitionCurrent < acquisitionTotal) ? Colors.red : Colors.green;
    }();

    final String acquisitionString = () {
      if (allVideos404) {return "404";}
      return "${acquisitionCurrent}/${acquisitionTotal}";
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

                // Header Details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${widget.label}",
                        style: Theme.of(context).textTheme.titleMedium,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ]
                  )
                ),

                Container(
                  margin: const EdgeInsets.fromLTRB(10, 0, 10, 0),
                  padding: const EdgeInsets.fromLTRB(2, 0, 2, 0),
                  decoration: BoxDecoration(
                    color: acquisitionColour.withValues(alpha: 0.7),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text("${acquisitionCurrent}/${acquisitionTotal}"),
                ),
              ]
            ),
            // Video content
            // Display info about each video
            if (_expanded) ...[
              ...widget.videos.map((video) => VideoCard(video: video, updateCardCallback: () {widget.updateCardCallback();}, activeTaskCardCallback: () {widget.updateCardCallback();})).toList(),
            ],
          ],
        )
      )
    );
  }
}

class VideoCard extends StatelessWidget {
  const VideoCard({
    super.key,
    required this.video,
    required this.updateCardCallback,
    required this.activeTaskCardCallback,
  });

  final Video video;
  final void Function () updateCardCallback;
  final void Function () activeTaskCardCallback;

  void toggleMonitored({required BuildContext context}) async {
    await LighthouseServerAPI().patchVideo(context: context, tidalID: video.tidalID, data: {"monitored": !video.monitored});
    updateCardCallback();
  }

  void onScanVideo({required BuildContext context}) async {
    await LighthouseServerAPI().scanVideo(context: context, tidalID: video.tidalID);
    activeTaskCardCallback();
  }

  void onAcquireVideo({required BuildContext context}) async {
    await LighthouseServerAPI().acquireVideo(context: context, tidalID: video.tidalID);
    activeTaskCardCallback();
  }

  @override
  Widget build(BuildContext context) {
    final Color videoAcquisitionColour =  switch (video.acquisitionState) {
      AcquisitionState.empty => Colors.red,
      AcquisitionState.pending => Colors.yellow,
      AcquisitionState.notFound => Colors.grey,
      AcquisitionState.acquired => Colors.green,
    };
    final String videoAcquisitionState = switch (video.acquisitionState) {
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
        ),

        Expanded(
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: "${video.name}",
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                TextSpan(
                  text: " - (${video.tidalID})",
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
            color: videoAcquisitionColour.withValues(alpha: 0.7),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(videoAcquisitionState),
        ),

        RowButton(icon: video.monitored ? Icons.bookmark : Icons.bookmark_outline, onTap: (() {toggleMonitored(context: context);})),

        RowButton(icon: Icons.document_scanner, onTap: (() {onScanVideo(context: context);})),

        RowButton(icon: Icons.cloud_download, onTap: (() {onAcquireVideo(context: context);})),
      ],
    );
  }
}
