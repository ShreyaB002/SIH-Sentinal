"""
test_phase11_correlation.py ? Unit Tests for Phase 11 & 12 (Event Correlation & Risk Engine).
"""

import sys
import time
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.correlation import (
    CompositeIncident,
    EventCorrelationEngine,
    RiskLevel,
    SecuritySignal,
)


class TestEventCorrelation(unittest.TestCase):
    def setUp(self):
        self.engine = EventCorrelationEngine(correlation_window_seconds=30.0, cooldown_seconds=2.0)

    def test_single_atomic_signal_no_composite(self):
        sig = SecuritySignal(
            signal_type="LOITERING",
            camera_id="cam_01",
            track_id=1,
            label="Person",
            confidence=0.90,
            metadata={"zone": "Zone A"},
        )
        inc = self.engine.ingest_signal(sig)
        self.assertIsNone(inc)

    def test_armed_intrusion_correlation(self):
        t0 = 1000.0
        # 1. Intrusion signal
        sig_intr = SecuritySignal(
            signal_type="INTRUSION",
            camera_id="cam_01",
            track_id=7,
            label="Person",
            confidence=0.88,
            metadata={"zone": "North Perimeter"},
            timestamp=t0,
        )
        self.assertIsNone(self.engine.ingest_signal(sig_intr))

        # 2. Weapon signal within correlation window
        sig_wpn = SecuritySignal(
            signal_type="WEAPON",
            camera_id="cam_01",
            track_id=7,
            label="Gun",
            confidence=0.85,
            timestamp=t0 + 2.0,
        )
        inc = self.engine.ingest_signal(sig_wpn)

        self.assertIsNotNone(inc)
        self.assertEqual(inc.risk_level, RiskLevel.CRITICAL)
        self.assertIn("Armed Perimeter Intrusion", inc.title)
        self.assertEqual(inc.involved_weapon, "Gun")
        self.assertIn(7, inc.involved_track_ids)

    def test_watchlist_target_breach_correlation(self):
        t0 = 2000.0
        # 1. Intrusion
        sig_intr = SecuritySignal(
            signal_type="INTRUSION",
            camera_id="cam_02",
            track_id=3,
            label="Person",
            confidence=0.92,
            metadata={"zone": "BOP Gate"},
            timestamp=t0,
        )
        self.engine.ingest_signal(sig_intr)

        # 2. Face Match
        sig_face = SecuritySignal(
            signal_type="FACE_MATCH",
            camera_id="cam_02",
            track_id=3,
            label="Target Bravo",
            confidence=0.89,
            metadata={"name": "Target Bravo"},
            timestamp=t0 + 1.0,
        )
        inc = self.engine.ingest_signal(sig_face)

        self.assertIsNotNone(inc)
        self.assertEqual(inc.risk_level, RiskLevel.CRITICAL)
        self.assertEqual(inc.involved_person_name, "Target Bravo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
