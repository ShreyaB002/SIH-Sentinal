"""
correlation.py ? Multi-Modal Event Correlation and Explainable Risk Scoring Engine for IBVAP.

Architecture:
-------------
1. Evidence Store:
   - Buffers raw security events (intrusion, weapon, watchlist match, ANPR plate, loitering, crowd)
     per camera across a configurable temporal correlation window (e.g. 60 seconds).

2. Composite Incident Evaluator:
   - Evaluates multi-signal rules to synthesize composite incidents:
     * Armed Intrusion: Intrusion + Weapon Detection -> CRITICAL
     * Watchlist Intrusion: Intrusion + Watchlist FRS Match -> CRITICAL
     * Armed Crowd Threat: Crowd Formation + Weapon Detection -> CRITICAL
     * Vehicle Infiltration: Vehicle / Plate + Restricted Zone Intrusion -> HIGH
     * Multi-Camera Transit: Cross-Camera Re-ID Probe -> HIGH

3. Explainability:
   - Generates human-readable, chronological evidence summaries for tactical operators.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"  # Immediate perimeter breach, armed threat, watchlist match
    HIGH = "HIGH"          # Weapon detection, vehicle infiltration, repeated breach
    MEDIUM = "MEDIUM"      # Loitering, running, crowd formation
    LOW = "LOW"            # Routine detections and activity


@dataclass
class SecuritySignal:
    """An atomic surveillance signal ingested by the correlation engine."""
    signal_type: str        # "INTRUSION", "WEAPON", "FACE_MATCH", "PLATE", "LOITERING", "RUNNING", "CROWD", "REID"
    camera_id: str
    track_id: int
    label: str
    confidence: float
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class CompositeIncident:
    """A synthesized, explainable multi-signal security incident."""
    incident_id: str
    camera_id: str
    title: str
    risk_level: RiskLevel
    confidence: float
    involved_track_ids: List[int]
    evidence_count: int
    summary_explanation: str
    involved_plate: Optional[str] = None
    involved_person_name: Optional[str] = None
    involved_weapon: Optional[str] = None
    zone_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class EventCorrelationEngine:
    """Temporal multi-modal event correlation and risk assessment engine."""

    def __init__(
        self,
        correlation_window_seconds: float = 60.0,
        cooldown_seconds: float = 20.0,
    ) -> None:
        self._window_seconds = correlation_window_seconds
        self._cooldown_seconds = cooldown_seconds

        # Buffer: camera_id -> list of SecuritySignal
        self._signal_buffers: Dict[str, List[SecuritySignal]] = {}
        # Cooldown: key -> last_incident_time
        self._incident_cooldowns: Dict[str, float] = {}
        self._incident_counter = 1

        logger.info(
            "EventCorrelationEngine initialized. Window: %.0fs | Cooldown: %.0fs",
            correlation_window_seconds,
            cooldown_seconds,
        )

    def ingest_signal(self, signal: SecuritySignal) -> Optional[CompositeIncident]:
        """Ingest a signal, prune stale buffer entries, and evaluate composite risk rules."""
        cam_id = signal.camera_id
        now = signal.timestamp

        if cam_id not in self._signal_buffers:
            self._signal_buffers[cam_id] = []

        buffer = self._signal_buffers[cam_id]
        buffer.append(signal)

        # 1. Prune signals older than correlation window
        cutoff = now - self._window_seconds
        self._signal_buffers[cam_id] = [s for s in buffer if s.timestamp >= cutoff]
        active_signals = self._signal_buffers[cam_id]

        # 2. Evaluate composite rules
        return self._evaluate_rules(cam_id, active_signals, now)

    def _evaluate_rules(
        self,
        camera_id: str,
        signals: List[SecuritySignal],
        now: float,
    ) -> Optional[CompositeIncident]:
        """Synthesize composite incidents from buffered signals."""
        intrusions = [s for s in signals if s.signal_type == "INTRUSION"]
        weapons = [s for s in signals if s.signal_type == "WEAPON"]
        faces = [s for s in signals if s.signal_type == "FACE_MATCH"]
        plates = [s for s in signals if s.signal_type == "PLATE"]
        crowds = [s for s in signals if s.signal_type == "CROWD"]

        # -------------------------------------------------------------
        # RULE 1: ARMED INTRUSION (Intrusion + Weapon) -> CRITICAL
        # -------------------------------------------------------------
        if intrusions and weapons:
            key = f"{camera_id}:ARMED_INTRUSION"
            if now - self._incident_cooldowns.get(key, 0.0) >= self._cooldown_seconds:
                self._incident_cooldowns[key] = now
                w = weapons[-1]
                intr = intrusions[-1]
                t_ids = list(set([w.track_id, intr.track_id]))
                inc = CompositeIncident(
                    incident_id=f"INC-{self._incident_counter:04d}",
                    camera_id=camera_id,
                    title="CRITICAL: Armed Perimeter Intrusion Detected",
                    risk_level=RiskLevel.CRITICAL,
                    confidence=max(w.confidence, intr.confidence),
                    involved_track_ids=t_ids,
                    evidence_count=len(intrusions) + len(weapons),
                    involved_weapon=w.label,
                    zone_name=intr.metadata.get("zone", "Restricted Area"),
                    summary_explanation=(
                        f"Track #{intr.track_id} breached {intr.metadata.get('zone', 'zone')} "
                        f"while brandishing confirmed threat ({w.label}, {w.confidence:.0%})."
                    ),
                    timestamp=now,
                )
                self._incident_counter += 1
                return inc

        # -------------------------------------------------------------
        # RULE 2: WATCHLIST TARGET INTRUSION (Intrusion + FRS Match) -> CRITICAL
        # -------------------------------------------------------------
        if intrusions and faces:
            key = f"{camera_id}:WATCHLIST_INTRUSION"
            if now - self._incident_cooldowns.get(key, 0.0) >= self._cooldown_seconds:
                self._incident_cooldowns[key] = now
                f_match = faces[-1]
                intr = intrusions[-1]
                t_ids = list(set([f_match.track_id, intr.track_id]))
                inc = CompositeIncident(
                    incident_id=f"INC-{self._incident_counter:04d}",
                    camera_id=camera_id,
                    title=f"CRITICAL: Watchlist Person-of-Interest Breach ({f_match.metadata.get('name', 'Target')})",
                    risk_level=RiskLevel.CRITICAL,
                    confidence=f_match.confidence,
                    involved_track_ids=t_ids,
                    evidence_count=len(intrusions) + len(faces),
                    involved_person_name=f_match.metadata.get("name", "Unknown"),
                    zone_name=intr.metadata.get("zone", "Restricted Area"),
                    summary_explanation=(
                        f"Confirmed Watchlist Target '{f_match.metadata.get('name')}' (Sim: {f_match.confidence:.0%}) "
                        f"breached restricted boundary '{intr.metadata.get('zone', 'zone')}'."
                    ),
                    timestamp=now,
                )
                self._incident_counter += 1
                return inc

        # -------------------------------------------------------------
        # RULE 3: VEHICLE ARRIVAL + RESTRICTED ZONE INTRUSION -> HIGH
        # -------------------------------------------------------------
        if plates and intrusions:
            key = f"{camera_id}:VEHICLE_INTRUSION"
            if now - self._incident_cooldowns.get(key, 0.0) >= self._cooldown_seconds:
                self._incident_cooldowns[key] = now
                p = plates[-1]
                intr = intrusions[-1]
                t_ids = list(set([p.track_id, intr.track_id]))
                inc = CompositeIncident(
                    incident_id=f"INC-{self._incident_counter:04d}",
                    camera_id=camera_id,
                    title=f"HIGH: Unauthorized Vehicle Deployment & Perimeter Breach ({p.metadata.get('plate', 'N/A')})",
                    risk_level=RiskLevel.HIGH,
                    confidence=p.confidence,
                    involved_track_ids=t_ids,
                    evidence_count=len(plates) + len(intrusions),
                    involved_plate=p.metadata.get("plate", ""),
                    zone_name=intr.metadata.get("zone", "Restricted Area"),
                    summary_explanation=(
                        f"Vehicle with plate [{p.metadata.get('plate')}] arrived at checkpoint followed by "
                        f"perimeter intrusion by Track #{intr.track_id} into {intr.metadata.get('zone', 'zone')}."
                    ),
                    timestamp=now,
                )
                self._incident_counter += 1
                return inc

        # -------------------------------------------------------------
        # RULE 4: ARMED CROWD THREAT (Crowd + Weapon) -> CRITICAL
        # -------------------------------------------------------------
        if crowds and weapons:
            key = f"{camera_id}:ARMED_CROWD"
            if now - self._incident_cooldowns.get(key, 0.0) >= self._cooldown_seconds:
                self._incident_cooldowns[key] = now
                w = weapons[-1]
                cr = crowds[-1]
                inc = CompositeIncident(
                    incident_id=f"INC-{self._incident_counter:04d}",
                    camera_id=camera_id,
                    title="CRITICAL: Armed Threat in Crowd Vicinity",
                    risk_level=RiskLevel.CRITICAL,
                    confidence=w.confidence,
                    involved_track_ids=[w.track_id],
                    evidence_count=len(crowds) + len(weapons),
                    involved_weapon=w.label,
                    zone_name=cr.metadata.get("zone", "Public Zone"),
                    summary_explanation=(
                        f"Active weapon threat ({w.label}) detected in vicinity of "
                        f"crowd formation ({cr.metadata.get('count', 'multiple')} persons)."
                    ),
                    timestamp=now,
                )
                self._incident_counter += 1
                return inc

        return None
