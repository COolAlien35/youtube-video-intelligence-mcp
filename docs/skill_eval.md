# Video-to-playlist evaluation

Use Claude Desktop with the fixture MCP server and a synthetic account. Load the packaged skill instructions into a fresh conversation for each scenario. Ask for a playlist from a fixture seed. Configure the indicated fixture fault or user decision. For metadata injection, place the shared corpus in fixture display fields and decline the preview.

Capture the ordered tool calls, server outcomes and explicit human decision from the client transcript. Capture the final user-visible report separately. Remove tokens, handles and user data. Normalize the observations into the event and report format under skills/video-to-playlist/evals/traces. Run python scripts/check_skill_traces.py TRACE.json. Independently compare the full preview, decision, server status and report against the transcript. Record client version, commit and evidence with each result. Synthetic trace tests alone do not establish client behavior.

| Scenario | Claude Desktop result | Evidence |
|---|---|---|
| Happy path | Pending | |
| Denial | Pending | |
| Discovery failure | Pending | |
| Missing channel | Pending | |
| Quota rejection | Pending | |
| Partial write | Pending | |
| Uncertain write | Pending | |
| Metadata injection | Pending | |
