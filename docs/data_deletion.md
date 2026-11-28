# Disconnecting an account and deleting data

## For users

1. Sign in to the MCP service as the owner of the connected account. Use disconnect or disconnect_google with the selected account_ref to revoke and remove that account's grant. The response reports whether Google confirmed revocation. The delete_data tool remains a stub in this development build. Contact the deployment operator privately to request deletion of other associated local records and obtain a receipt.
2. To revoke the Google grant yourself, remove the app in [Google Account permissions](https://security.google.com/settings/security/permissions). You do not need a working Google grant to request deletion of local records.
3. Keep the request reference or private acknowledgment. The operator must confirm completion within seven calendar days. A failed tool call is not a receipt. **Playlists and videos already created on YouTube stay in your YouTube account** after you disconnect or delete your local service data; manage or delete them on YouTube directly if you also want them removed there.

## For operators

Verify the requester through the service identity. Resolve records from that verified issuer and subject, never from an unverified account name in a message. Accept a local deletion request even when Google authorization has expired.

Record a scoped deletion request and deadline, and append deletion_requested to the compliance journal. On disconnect, halt account use, revoke the grant with Google when applicable, and record consent_revoked. Remove token material, account signals, scoped caches, derived outputs, proposals and operation items for this principal. Apply the same purge deadline to associated local records after consent revocation. Keep records of other principals intact.

Use ComplianceLedger.forget_principal after the final principal-linked journal event to erase the lookup association; avoid retaining a second copy in receipts or logs. Verify the account cannot be used and scoped records are absent before confirming completion privately. Follow up on incomplete purges before the deadline; never confirm completion based only on request creation. For retained backups the operator must document expiry and reapply outstanding deletions before restoring service.

Normal cleanup expires unexecuted proposals at five minutes, removes terminal proposals and completed/failed operations within 24 hours, and refreshes or deletes stored API data within 30 days. A seven-day deletion deadline takes precedence. A team-approved lifetime for unlinked operational evidence remains pending. [Privacy policy](privacy_policy.md)
