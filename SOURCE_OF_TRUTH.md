# Source of truth

> **Canonical production repository**

- Domain: `blog.stargateedu.co.kr`
- Role: STARGATE blog and RSS content hub
- Repository: `DongsooJung/stargate-blog-hub`
- Effective date: 2026-08-05

## Editing policy

1. Make production changes in this repository only.
2. Do not overwrite `main` from `DongsooJung/DongsooJung` snapshot or `mirror/*` branches.
3. Use environment variables or GitHub Secrets for credentials.
4. Validate the live domain after changes that affect deployment.
5. If this source moves, update `DongsooJung/DongsooJung/DOMAIN_SOURCES.md` and the Notion GitHub dashboard.

The profile repository may retain reference snapshots, but those snapshots are not authorized deployment sources.
