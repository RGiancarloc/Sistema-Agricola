"""Configuracion de pytest: base de datos aislada y seed de sesion."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Base de datos aislada ANTES de importar la aplicacion.
_TMP_DB = Path(tempfile.gettempdir()) / "agricola_test.db"
if _TMP_DB.exists():
    try:
        _TMP_DB.unlink()
    except OSError:
        pass
os.environ["SA_DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ.setdefault(
    "SA_CONFIG_DIR", str(Path(__file__).resolve().parents[2] / "config")
)

import pytest  # noqa: E402

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.seeds.generate import seed_all  # noqa: E402


@pytest.fixture(scope="session")
def seeded() -> bool:
    init_db()
    with SessionLocal() as session:
        seed_all(session, reset=True)
    return True


@pytest.fixture()
def session(seeded: bool):
    with SessionLocal() as s:
        yield s
