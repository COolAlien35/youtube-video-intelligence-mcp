# Privacy policy for YouTube Video Intelligence

**Phase 5 fixture development edition · 28 November 2026.** The current service runs with synthetic fixtures. Live YouTube access is disabled. The information below describes the authorized service design and the rights users must have before a live release.

## What the service uses

The service uses the issuer and subject from your verified sign-in to separate your records from other users. Connecting Google links your account to that identity. The authorized design stores the scopes you grant and an encrypted refresh token to maintain your connection. Read access is requested first. Playlist creation requires an additional write scope and your approval of the exact preview.

With permission, the service can use video and channel metadata, liked videos, subscriptions and playlist items to find related educational material, describe engagement and prepare playlists. It also records your constraints, selected items, operation outcomes and consent or deletion events. YouTube does not provide watch history through this workflow. Request identifiers support diagnostics. Credentials, OAuth codes, callback state and raw account payloads must stay out of logs.

## Storage, access and deadlines

Only your authorized operations may use your account data. Platform-wide quotas and compliance determinations are shared. The journal keeps minimal event types, timestamps and evidence references. Account events use an opaque reference with a separate association that operators remove during deletion.

- Unexecuted proposals expire after five minutes. Terminal proposals and completed or failed operation records are removed within 24 hours.
- Stored YouTube API data must be refreshed or deleted within 30 days. Revocation and deletion requests start an earlier deadline.
- The service must purge associated data as soon as possible and within seven calendar days of revocation or a deletion request. Disconnecting stops future authorized access. Deleting local records leaves YouTube-hosted playlists and videos in your YouTube account.

## Account analytics

In the fixture build, engagement analysis caches normalized account signals and selected video details under your verified service identity. These can include channel, category, playlist and video identifiers, durations and source timestamps. The account-signal cache defaults to 24 hours. The API exposes up to 1,000 recent likes; dates on those entries describe video publication. Access tokens remain transient. A disconnect removes this analytics cache immediately, including when remote revocation cannot be confirmed. Other local data subject to a deletion request must be purged within seven calendar days.

## Disconnecting or requesting deletion

The authenticated disconnect_google tool removes the selected grant and immediately purges the engagement cache for your service identity. The delete_data tool is still a stub. A successful tool response or an operator receipt is required to establish that a request was received. For a private development deployment, contact its operator directly for a receipt and completion confirmation. Keep account identifiers and credentials out of public project issues. See the [deletion guide](data_deletion.md).

You can independently revoke access in [Google Account permissions](https://security.google.com/settings/security/permissions). The live service uses YouTube API Services and is subject to the [YouTube Terms of Service](https://www.youtube.com/t/terms) and [Google Privacy Policy](https://policies.google.com/privacy). Before taking real accounts, the operator must publish a private contact channel and verify the deletion flow.
