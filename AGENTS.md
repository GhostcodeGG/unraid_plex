# Repository Guidelines

## Project Structure & Module Organization
- Root scripts and compose files live in `./` for Unraid/Plex deployment; persistent configs usually mount from `/mnt/user/appdata/plex`.
- Docker build context uses project root; review `docker-compose.yml` and any `Dockerfile` siblings for service wiring and volume paths.
- Logs/config outputs land in bind-mounted host paths set in compose; avoid committing generated data.

## Build, Test, and Development Commands
- `docker compose build` — rebuild images after Dockerfile or dependency changes.
- `docker compose up -d` — start stack in background; use without `-d` during debugging to stream logs.
- `docker compose logs -f plex` — follow Plex container logs.
- `docker compose exec plex bash` — open a shell inside the Plex container for inspection.

## Coding Style & Naming Conventions
- Shell/YAML: two-space indent; keep keys kebab-case for labels and lowercase for service names.
- Dockerfiles: keep one concern per layer; order as base, packages, app files, then cleanup.
- Env files: uppercase keys with `_`; avoid committing secrets—use Unraid GUI secrets or `.env` excluded from VCS.

## Testing Guidelines
- No formal test suite; exercise changes by starting containers locally and verifying Plex UI and media scanning.
- Prefer `docker compose up` (foreground) on first run to watch logs for permission or path errors.
- If adding scripts, include a `--dry-run` or `--help` mode and document usage inline.

## Commit & Pull Request Guidelines
- Use concise, action-focused commits (e.g., `fix: adjust plex volume paths`, `feat: add healthcheck`); group related changes.
- Pull requests: summarize intent, list key changes, note manual test steps (commands run, results), and link issues/Unraid forum context when applicable.
- Include screenshots/log snippets when changes affect Plex UI or container behavior for quicker review.

## Security & Configuration Tips
- Never commit Plex tokens or claims; pass via Unraid secrets or runtime env vars.
- Validate host paths and UID/GID mappings to avoid permission leaks; keep media directories read-only when possible.
- Restrict network exposure: rely on reverse proxy/auth if exposing Plex beyond local network.