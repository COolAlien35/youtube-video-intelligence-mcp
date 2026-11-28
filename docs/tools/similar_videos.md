# Similar Videos

Call `similar_videos` with a seed such as `{"seed":"SYNV_000000"}`. The authenticated fixture service accepts a bare video ID, watch URL, Shorts URL or youtu.be link. Each form uses the same canonical ID and principal-scoped cache entry.

One search page supplies up to 50 references. The service returns up to ten ranked videos with YouTube links, supplied channel titles, durations in seconds and short explanations. Unknown durations are null. The candidate count measures distinct available videos after exclusions. An empty result distinguishes an empty search from a page containing only excluded references.

The video profile assigns 50% to title, 30% to description, 15% to tags and 5% to category. Without seed tags, the interim ranker distributes their weight proportionally across the remaining fields. Applied weights appear in the result. The score describes metadata similarity within the bounded pool. It does not assess quality or accuracy. [Input schema](similar_videos.input.schema.json) · [Output schema](similar_videos.output.schema.json)
