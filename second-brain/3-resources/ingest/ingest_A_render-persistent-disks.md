# Render Persistent Disks and Single-Instance Behaviour

## Source

Render official documentation: [Persistent Disks](https://docs.render.com/disks), [Instance Types](https://docs.render.com/instance-types)

## Ingested by / date

Person A · 2026-11-22

## Summary

Render offers persistent disks that survive deploys and restarts, mounted at a user-specified path (e.g. `/var/data`). Unlike ephemeral filesystem storage that is wiped on every deploy, persistent disks retain data across the full lifecycle of a service. However, persistent disks impose a critical architectural constraint: only a single instance can mount a given disk at a time. This means horizontal scaling (multiple instances) is not available for services that rely on a persistent disk. This is relevant because the project plans to use SQLite on a persistent disk, which inherently requires single-writer access. Persistent disks are available only on paid instance types — the free tier does not support them. The team must confirm the specific plan and pricing before provisioning.

## Key facts

- Persistent disks survive deploys, restarts, and manual restarts (source: Render Disks docs)
- Only **one instance** can mount a persistent disk at a time — no horizontal scaling (source: Render Disks docs)
- Persistent disks require a **paid instance type** (Starter and above) (source: Render Instance Types)
- Disk size can be increased after creation but **not decreased** (source: Render Disks docs)
- Disks are tied to a single service and cannot be shared across services (source: Render Disks docs)
- Data on the disk persists even if the service is suspended (source: Render Disks docs)

## Relevance

- **SRS §6** (deployment architecture): The deployment target is a Render web service with `/var/data` for SQLite storage
- **ADR-02** (SQLite as primary store): Single-instance constraint aligns with SQLite's single-writer model
- **ADR-07** (deployment): Architecture must account for single-instance limitation

## Open questions / risks

- What is the exact cost of the cheapest paid plan that supports persistent disks? Must be confirmed before Phase 2.
- If the service needs to restart, is there a window where data is inaccessible?
- What is the maximum disk size, and is it sufficient for projected growth?
- Backup strategy: Render doesn't provide automatic disk backups — a manual or scripted approach is needed.

## Links

- [[Render Persistent Disks]]: https://docs.render.com/disks
- [[Render Instance Types]]: https://docs.render.com/instance-types
- [[ADR-02 SQLite]]: docs/architecture/ (pending)
