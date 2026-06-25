# Deploying FinSight

FinSight runs as a container on the shared **`infra`** Docker network and is consumed by the Mira
agent over MCP at `http://finsight:8000/mcp`. It has **no published host port** — Mira reaches it
container-to-container. It uses the infra **Postgres** (`finsight` DB) and **MinIO**
(`finsight-reports` bucket); it needs no DB/object-store of its own.

```
infra network
  ├─ infra-postgres  (finsight DB)
  ├─ infra-minio     (finsight-reports bucket)
  ├─ finsight        ← this app (MCP at /mcp, bearer-auth)
  └─ assistant-agent (Mira) ── http://finsight:8000/mcp ──▶ finsight
```

## Prerequisites

1. **The shared infra stack is up** — it owns the network and auto-provisions the DB + bucket:
   ```bash
   cd ../infra && docker compose up -d
   ```
   (Provisioned by `infra/postgres/init/03-create-finsight-db.sh` and the `finsight-reports`
   entry in infra's `minio-init`. On an already-running infra they were created once by hand;
   a fresh `infra` rebuild creates them automatically.)
2. **`.env` is filled** (copy from `.env.example`): `GEMINI_API_KEY`, `MCP_AUTH_TOKEN` (the bearer
   Mira sends), and the `SSI_*` credentials. Put the SSI RSA private key PEM at
   `secrets/ssi_private_key.pem` (mounted read-only; never baked into the image).

## Manual deploy (runs the service)

```bash
cd fin-sight
docker compose up -d --build
```

The container runs `alembic upgrade head` then `uvicorn`. There's no published port, so health-check
from inside the container (or from Mira's container):

```bash
docker exec finsight .venv/bin/python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/v1/health').read())"
```

`compose` overrides the localhost-oriented `.env` defaults to in-network names
(`DATABASE_URL → postgres:5432`, `MINIO_ENDPOINT → minio:9000`).

## Connecting Mira (the MCP client)

Mira is multi-tenant, so an `auth="none"` server needs **two** things — an `MCP_SERVERS` entry **and**
a per-owner static token in Mira's encrypted secret store (inline `headers` alone are ignored):

1. Add to Mira's `.env` `MCP_SERVERS` array:
   ```json
   {"name":"finsight","transport":"http","url":"http://finsight:8000/mcp","auth":"none",
    "headers":{"Authorization":"Bearer <MCP_AUTH_TOKEN>"},
    "read_only_tools":["get_stock_analysis","search_reports","get_report_metrics","list_facets",
      "ask_report_pdf","ssi_daily_ohlc","ssi_securities","ssi_index_components","ssi_daily_price",
      "ssi_my_positions","ssi_my_cash_balance","ssi_my_orders","ssi_my_deriv_positions"]}
   ```
2. Store the owner's `mcp_static` token (reads the token from the entry's `Authorization` header or
   `MCP_FINSIGHT_TOKEN`). From the Mira checkout (which has `scripts/`):
   ```bash
   uv run python -m scripts.import_owner_secrets   # idempotent; targets the owner DB
   ```
3. Restart Mira so it loads the new server and rebuilds the runtime:
   ```bash
   docker compose up -d      # in the assistant-agent dir
   ```
   Confirm in the logs: `mcp.connected server=finsight tools=13`. The 13 tools register as
   `mcp__finsight__*`.

`fin-sight`'s `MCP_AUTH_TOKEN` and the value in Mira's header/secret **must match**.

## Automated CD (GitHub Actions, self-hosted)

- **`ci.yml`** — on PRs and pushes to `master`: ruff, format check, unit tests, and a docker build
  (GitHub-hosted runners). This gates the deploy.
- **`deploy.yml`** — on CI success on `master` (or manual *Run workflow*), on a `[self-hosted, macOS]`
  runner: pulls `master` into the deploy clone, `docker compose up -d --build`, and smoke-checks
  health from inside the container.

### One-time setup on the Mac (mirrors assistant-agent)

1. **Register a self-hosted runner** for the fin-sight repo with the `macOS` label:
   GitHub → repo **Settings → Actions → Runners → New self-hosted runner** → follow the macOS steps,
   then install it as a service (`./svc.sh install && ./svc.sh start`). (Without this, the deploy job
   queues forever waiting for a runner — don't merge to `master` until it's registered.)
2. **Create the deploy clone** with symlinked secrets so creds have a single source of truth and
   `git reset --hard` never clobbers them:
   ```bash
   git clone <repo-url> ~/srv/fin-sight
   cd ~/srv/fin-sight
   ln -s ~/Documents/Projects/fin-sight/.env .env
   ln -s ~/Documents/Projects/fin-sight/secrets secrets
   ```
3. Ensure the **`infra` network exists** (`cd ../infra && docker compose up -d`) — the compose file
   joins it as `external`.

After that, merging to `master` auto-deploys; or trigger manually via **Actions → Deploy → Run workflow**.

## Notes / gotchas

- **No published port** is deliberate (defense in depth): finsight is only reachable on the infra
  network, behind the bearer token. Health-check from inside the container.
- **DNS-rebinding host check is disabled** in `build_mcp_server` — the MCP SDK defaults to
  localhost-only and would `421` a client connecting as `finsight:8000`. Safe here (private network +
  bearer auth); it targets browser-reachable localhost servers, which this isn't.
- **A new `MCP_SERVERS` entry needs a Mira restart**; setting the `mcp_static` token needs a runtime
  rebuild (also a restart).
- **Re-consent / token rotation:** rotate `MCP_AUTH_TOKEN` in fin-sight's `.env`, update Mira's header
  + re-run the owner-secrets import, then restart both.
