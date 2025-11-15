"""Utilities to keep workshop notebooks robust."""

from __future__ import annotations

import os
from typing import Iterable, List


def ensure_notebook_env(required_vars: Iterable[str]) -> None:
    """
    Validate that all required environment variables are present.

    Raises a ValueError with a helpful hint when one or more variables are missing.
    """
    missing: List[str] = []
    for var in required_vars:
        value = os.getenv(var)
        if value in (None, ""):
            missing.append(var)

    if missing:
        raise ValueError(
            "Es fehlen notwendige Environment Variablen: "
            f"{', '.join(missing)}\n"
            "Bitte tools_and_data/.env (aus .env.template) ausfüllen "
            "und danach das Notebook erneut starten."
        )

    print("✅ Alle benötigten Environment Variablen sind gesetzt")
