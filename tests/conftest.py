from __future__ import annotations

import os
import sys
from pathlib import Path

from hypothesis import HealthCheck, settings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

settings.register_profile(
    "extreme_ci",
    derandomize=True,
    deadline=1000,
    suppress_health_check=[HealthCheck.too_slow],
)

if os.getenv("MEDF_EXTREME", "").strip() == "1":
    settings.load_profile("extreme_ci")
