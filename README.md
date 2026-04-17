# finance-dashboard

Self-hosted personal finance tracker. Aggregates bank transactions from Revolut, ČSOB SK and Tatra banka via the Enable Banking PSD2 API. Runs on a Raspberry Pi, accessible only over Tailscale.

**Status:** 🚧 pre-MVP, not ready for use.

## Stack

- Python 3.11+ / FastAPI / SQLite
- HTMX + Jinja2 + Tailwind (no build step)
- Argon2 auth + sessions
- systemd service + timer
- Tailscale-only network binding

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
