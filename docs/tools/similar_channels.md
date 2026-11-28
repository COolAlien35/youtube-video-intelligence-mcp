# similar_channels

Supply a YouTube channel ID, an exact @handle, a channel URL or a handle URL with a tab such as /videos. An authenticated MCP client can try the following fixture request.

```json
{"channel":"@syn_prism"}
```

The response contains the seed, up to ten ranked channels, canonical YouTube links, scores, explanations, attribution and a request ID. Each explanation lists shared metadata terms and the relative contribution of each matching field. A zero score means the available text had no overlapping terms. Synthetically generated metadata supplies the current results. Similarity describes overlap in that metadata and makes no claim about accuracy or quality.

The workflow searches one page of up to 50 references. The candidate count is the number of distinct available channels scored after removing the seed. An empty search returns `no_candidates_found`. When all references are excluded, the result contains `all_candidates_excluded`. Both outcomes have a human-readable explanation.

An unknown exact reference returns `NOT_FOUND_OR_UNAVAILABLE`. Legacy URLs and malformed input return `INVALID_INPUT`. A quota or rate rejection has a structured error and request ID. Rate limits also include `retry_after` in seconds. The service takes the principal from the authenticated request.

[Input schema](similar_channels.input.schema.json) · [Output schema](similar_channels.output.schema.json)
