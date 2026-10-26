"""Utilidades de reproducibilidad: RNG derivado de una semilla maestra."""
from __future__ import annotations

import numpy as np

from app.core.config import settings


def master_rng(seed: int | None = None) -> np.random.Generator:
    """Generador NumPy a partir de la semilla maestra (o una dada)."""
    return np.random.default_rng(settings.seed if seed is None else seed)


def derived_seed(*parts: object, base: int | None = None) -> int:
    """Semilla estable derivada de etiquetas (para subprocesos reproducibles)."""
    h = (settings.seed if base is None else base) % (2**32)
    for p in parts:
        for ch in str(p):
            h = (h * 16777619 ^ ord(ch)) % (2**32)
    return h
