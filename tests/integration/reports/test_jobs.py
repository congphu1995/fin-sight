"""End-to-end tests of the pipeline are gated on Postgres + MinIO availability.

The pipeline uses Postgres-specific SQL features (ON CONFLICT, FOR UPDATE SKIP
LOCKED, JSONB) so an in-memory SQLite stand-in is not enough. Full coverage
runs under `docker compose up`. The service-level logic is covered by unit
tests in tests/unit/reports/.
"""

import pytest

pytestmark = pytest.mark.skip(reason="requires docker compose Postgres + MinIO")
