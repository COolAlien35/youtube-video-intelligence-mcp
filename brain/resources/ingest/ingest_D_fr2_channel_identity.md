# Exact channel identity and bounded discovery

Person D · 2026-11-28 · FR-2a–2h, IF-16b

YouTube documents ID-based channel URLs and handle URLs as distinct ways to identify the same channel. Handles support international characters and can appear percent-encoded in copied links. Handle spelling is case-insensitive. Local parsing checks reference syntax. The exact provider lookup determines whether the channel exists. [Channel URLs](https://support.google.com/youtube/answer/6180214) · [Handle guidelines](https://support.google.com/youtube/answer/11585688)

The official channels.list method accepts an ID or forHandle filter and also has a separate legacy forUsername filter. The FR-2 contract accepts IDs and handles. Users with a legacy or custom URL receive guidance to supply a supported exact reference. Search by display name would conflate distinct channels, as the synthetic same-name pair demonstrates. [API reference](https://developers.google.com/youtube/v3/docs/channels/list) · [Fixtures](https://github.com/COolAlien35/youtube-video-intelligence-mcp/pull/63)

A single candidate page bounds quota exposure but limits coverage. The service includes the pool bound and explains empty results. Confirm the pool size with B and the ranking profile with C before team sign-off. [Coordination](https://github.com/COolAlien35/youtube-video-intelligence-mcp/issues/61)
