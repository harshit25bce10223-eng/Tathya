# Release deployment

Use the dedicated `deploy/compose.production.yml` for a fresh PostgreSQL deployment. It runs a single API worker (the audit job executor is in-process), stores uploads and passport signing keys in persistent volumes, installs OCR dependencies, and uses Caddy for HTTPS. The database has no public port. Runtime secrets, model caches and uploaded files are excluded from Docker build context.

1. On a Linux server with Docker Compose, copy `deploy/.env.example` to `deploy/.env.production`. Set an owned domain pointing to that server, contact email, admin email and three different random secrets. Use a URL-safe database password. Keep the secrets file private; it is ignored by Git.
2. From the repository root, run `docker compose --env-file deploy/.env.production -f deploy/compose.production.yml config --quiet` then `docker compose --env-file deploy/.env.production -f deploy/compose.production.yml up -d --build`.
3. Check `/health`, upload a synthetic AI document plus source, review the actual findings and verify its signed passport. Confirm uploads and keys survive a restart before admitting users. Model downloads require outbound network and adequate memory/disk.
4. Back up PostgreSQL, document storage and signing volumes together. Never regenerate signing keys for an existing installation. The bootstrap checks existing table columns and refuses an incompatible database; it does not silently migrate legacy data. Review migrations separately before switching an existing database.

This environment has no Docker executable or authenticated hosting target. YAML was parsed and source checks passed, but the image build, TLS issuance, fresh-container startup and restart persistence have **not** been executed here. The file is a release candidate, not evidence of a live deployment.

Reference: [Compose required variables](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/), [Caddy body limits](https://caddyserver.com/docs/caddyfile/directives/request_body), [PostgreSQL image volume layout](https://hub.docker.com/_/postgres).

# Mobile release

`mobile/eas.json` provides an internal Android APK profile and a production profile. Use the installed SDK 57 APIs and Expo Router. Set `EXPO_PUBLIC_API_URL` to the HTTPS server origin before building; never embed credentials. Native sessions use SecureStore; web sessions stay in memory. Camera and notifications ask permission when requested. Local completion alerts work while the audit screen is open; background push delivery is not implemented.

On an authenticated Expo account, run `npx eas-cli@latest build:configure`, then `npx eas-cli@latest build --platform android --profile preview`. Review the resulting APK on a physical device: login, document/source order, upload, camera/OCR, reviewer permissions, QR verification, stale-score gating, sign out and offline/error handling. Production store submission also needs the owner's developer accounts and signing setup. Android/iOS Hermes and web exports passed locally; those are bundles, **not signed installable APKs**.
