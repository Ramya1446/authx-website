"""
authenticity_scorer.py — Journal AuthX Contribution 2
======================================================
Unified Authenticity Scoring Engine.

FIXED: Context-aware scoring.
  - context="register"  → blockchain/hash components are NEUTRAL (new content 
                           can't have a record yet; not penalised for it)
  - context="verify"    → blockchain/hash components are active signals
  - context="analyze"   → pure forensics only, no blockchain/hash weight

Metrics:
  - Authenticity Score : 0–100  (100 = fully authentic)
  - Trust Score        : 0–100  (confidence-weighted)
  - Risk Level         : LOW | MEDIUM | HIGH | CRITICAL
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
import math
import numpy as np


# ─────────────────────────────────────────────────────────────
#  RISK BANDS
# ─────────────────────────────────────────────────────────────
RISK_BANDS = [
    (80, "LOW",      "Content appears authentic with high confidence."),
    (55, "MEDIUM",   "Some anomalies detected. Manual review recommended."),
    (30, "HIGH",     "Significant tampering indicators found. Treat with caution."),
    (0,  "CRITICAL", "Strong evidence of AI generation or malicious tampering."),
]


# ─────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

@dataclass
class ComponentScore:
    name: str
    raw_score: float      # 0–1 (higher = more suspicious)
    weight: float
    contribution: float   # raw_score * weight (in suspicion space)
    confidence: float
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuthenticityReport:
    authenticity_score: float
    trust_score: float
    risk_level: str
    risk_description: str
    modality: str
    context: str = "register"

    components: List[ComponentScore] = field(default_factory=list)

    tamper_regions_count: int = 0
    top_tamper_regions: List[Dict] = field(default_factory=list)

    blockchain_verified: bool = False
    exact_hash_match: bool = False
    cross_modal_consistent: Optional[bool] = None

    recommendations: List[str] = field(default_factory=list)
    raw_signals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "authenticity_score": round(self.authenticity_score, 2),
            "trust_score":        round(self.trust_score, 2),
            "risk_level":         self.risk_level,
            "risk_description":   self.risk_description,
            "modality":           self.modality,
            "context":            self.context,
            "components":         [c.to_dict() for c in self.components],
            "localization": {
                "tamper_regions_count": self.tamper_regions_count,
                "top_tamper_regions":   self.top_tamper_regions,
            },
            "evidence": {
                "blockchain_verified":    self.blockchain_verified,
                "exact_hash_match":       self.exact_hash_match,
                "cross_modal_consistent": self.cross_modal_consistent,
            },
            "recommendations": self.recommendations,
        }


# ─────────────────────────────────────────────────────────────
#  SCORER
# ─────────────────────────────────────────────────────────────

class AuthenticityScorer:
    """
    Context-aware authenticity scoring.

    Key design decisions
    --------------------
    1.  Forensic tamper_probability is the PRIMARY signal (60% weight during
        registration, 45% during verification).

    2.  During REGISTRATION the file is new — it cannot have a blockchain
        record or hash match yet. These components get 0 weight so they
        never penalise legitimate new uploads.

    3.  During VERIFICATION a blockchain record IS expected for authentic
        content, so missing one is a real signal (15% weight).

    4.  Localization density is a minor signal; we cap its influence at 10%
        and normalise against modality-specific baselines so that a video
        with naturally detected motion regions isn't mis-scored.

    5.  Trust Score = Authenticity Score × mean_confidence. It drops when
        forensic confidence is low (uncertain result), not when the content
        is new.
    """

    # ── Weights by context ──────────────────────────────────
    WEIGHTS = {
        # context          forensic  cross_modal  blockchain  hash   localization
        "register": dict(forensic=0.70, cross_modal=0.20, blockchain=0.00, hash=0.00, loc=0.10),
        "verify":   dict(forensic=0.50, cross_modal=0.15, blockchain=0.20, hash=0.10, loc=0.05),
        "analyze":  dict(forensic=0.80, cross_modal=0.10, blockchain=0.00, hash=0.00, loc=0.10),
    }

    # Modality-specific baselines: how many localization regions are
    # "normal" for authentic content of that type.
    # Above this baseline the extra regions count as suspicious.
    REGION_BASELINE = {
        "image": 1,
        "audio": 2,
        "video": 4,   # Video naturally has more regions (frame differences etc.)
        "text":  1,
        "unknown": 2,
    }

    def score(
        self,
        forensic_report,
        cross_modal_result: Optional[dict] = None,
        blockchain_verified: bool = False,
        exact_hash_match: bool = False,
        context: str = "register",   # "register" | "verify" | "analyze"
    ) -> AuthenticityReport:

        w = self.WEIGHTS.get(context, self.WEIGHTS["register"])
        components: List[ComponentScore] = []
        modality = getattr(forensic_report, "modality", "unknown")

        # ── 1. Forensic analysis ─────────────────────────────
        fp   = float(forensic_report.tamper_probability)   # 0=clean 1=tampered
        fcon = float(forensic_report.confidence)

        # Confidence-dampen: if confidence is low, pull fp toward 0.3 (uncertain)
        effective_fp = fp * fcon + 0.3 * (1.0 - fcon)

        components.append(ComponentScore(
            name="forensic_analysis",
            raw_score=effective_fp,
            weight=w["forensic"],
            contribution=effective_fp * w["forensic"],
            confidence=fcon,
            summary=self._forensic_summary(forensic_report),
        ))

        # ── 2. Cross-modal consistency ───────────────────────
        cm_score      = 0.0
        cm_confidence = 0.5
        cm_consistent: Optional[bool] = None
        cm_summary    = "No cross-modal data provided."

        if cross_modal_result:
            cm_score      = float(cross_modal_result.get("inconsistency_score", 0.0))
            cm_confidence = float(cross_modal_result.get("confidence", 0.5))
            cm_consistent = cross_modal_result.get("is_consistent", True)
            cm_summary    = cross_modal_result.get("summary", "Cross-modal check completed.")

        components.append(ComponentScore(
            name="cross_modal_consistency",
            raw_score=cm_score,
            weight=w["cross_modal"],
            contribution=cm_score * w["cross_modal"],
            confidence=cm_confidence,
            summary=cm_summary,
        ))

        # ── 3. Blockchain verification ───────────────────────
        # During "register": weight=0, so it doesn't matter what bc_score is.
        # During "verify":   missing record IS suspicious.
        if context == "register":
            bc_score    = 0.0
            bc_conf     = 0.5
            bc_summary  = "New content — blockchain record will be created."
        elif blockchain_verified:
            bc_score    = 0.0
            bc_conf     = 0.95
            bc_summary  = "On-chain registration confirmed."
        else:
            bc_score    = 0.5   # Not verified during verify = moderate red flag
            bc_conf     = 0.7
            bc_summary  = "No blockchain record found — ownership unverified."

        components.append(ComponentScore(
            name="blockchain_verification",
            raw_score=bc_score,
            weight=w["blockchain"],
            contribution=bc_score * w["blockchain"],
            confidence=bc_conf,
            summary=bc_summary,
        ))

        # ── 4. Hash integrity ────────────────────────────────
        # Only meaningful during "verify".
        if context == "register":
            hash_score   = 0.0
            hash_conf    = 0.5
            hash_summary = "New registration — hash will be stored."
        elif exact_hash_match:
            hash_score   = 0.0
            hash_conf    = 1.0
            hash_summary = "SHA-256 exact match — file integrity confirmed."
        else:
            hash_score   = 0.3
            hash_conf    = 0.8
            hash_summary = "No exact hash match — file may have been modified."

        components.append(ComponentScore(
            name="hash_integrity",
            raw_score=hash_score,
            weight=w["hash"],
            contribution=hash_score * w["hash"],
            confidence=hash_conf,
            summary=hash_summary,
        ))

        # ── 5. Localization density ──────────────────────────
        regions   = getattr(forensic_report, "localization", [])
        n_regions = len(regions)

        # Only count regions ABOVE the modality baseline as suspicious
        baseline     = self.REGION_BASELINE.get(modality, 2)
        excess       = max(0, n_regions - baseline)
        # Normalise: 5 excess regions → score 0.5, 10+ → 1.0
        loc_score    = min(excess / 10.0, 1.0)

        components.append(ComponentScore(
            name="localization_density",
            raw_score=loc_score,
            weight=w["loc"],
            contribution=loc_score * w["loc"],
            confidence=0.75,
            summary=(f"{n_regions} tamper region(s) localised "
                     f"({excess} above {modality} baseline of {baseline})."
                     if n_regions else "No specific tamper regions identified."),
        ))

        # ── Aggregate suspicion (0–1) ─────────────────────────
        total_suspicion = min(sum(c.contribution for c in components), 1.0)

        # ── Authenticity Score (0–100) ────────────────────────
        authenticity_score = (1.0 - total_suspicion) * 100.0
        authenticity_score = max(0.0, min(100.0, authenticity_score))

        # ── Trust Score: confidence-weighted ─────────────────
        # Use only the components that have non-zero weight
        total_weight   = sum(c.weight for c in components if c.weight > 0)
        mean_confidence = (
            sum(c.confidence * c.weight for c in components if c.weight > 0)
            / max(total_weight, 1e-6)
        )
        trust_score = max(0.0, min(100.0, authenticity_score * mean_confidence))

        # ── Risk level ────────────────────────────────────────
        risk_level, risk_desc = self._risk_level(authenticity_score)

        # ── Top tamper regions ────────────────────────────────
        top_regions       = sorted(regions, key=lambda r: -r.severity)[:5]
        top_regions_dicts = [r.to_dict() for r in top_regions]

        # ── Recommendations ───────────────────────────────────
        recs = self._recommendations(
            authenticity_score, forensic_report, blockchain_verified,
            exact_hash_match, cm_consistent, n_regions, context
        )

        return AuthenticityReport(
            authenticity_score=authenticity_score,
            trust_score=trust_score,
            risk_level=risk_level,
            risk_description=risk_desc,
            modality=modality,
            context=context,
            components=components,
            tamper_regions_count=n_regions,
            top_tamper_regions=top_regions_dicts,
            blockchain_verified=blockchain_verified,
            exact_hash_match=exact_hash_match,
            cross_modal_consistent=cm_consistent,
            recommendations=recs,
            raw_signals={
                "forensic_tamper_probability": fp,
                "forensic_confidence":         fcon,
                "effective_forensic_score":    round(effective_fp, 4),
                "total_suspicion":             round(total_suspicion, 4),
                "forensic_artifacts":          getattr(forensic_report, "artifacts", []),
            },
        )

    # ─────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────

    def _risk_level(self, auth_score: float):
        for threshold, level, desc in RISK_BANDS:
            if auth_score >= threshold:
                return level, desc
        return "CRITICAL", RISK_BANDS[-1][2]

    def _forensic_summary(self, report) -> str:
        prob = report.tamper_probability
        arts = getattr(report, "artifacts", [])[:3]
        art_str = ", ".join(arts) if arts else "none detected"
        if prob < 0.15:
            return f"Very low tampering probability ({prob:.1%}). Forensics are clean."
        if prob < 0.35:
            return f"Low-moderate signals ({prob:.1%}). Artifacts: {art_str}."
        if prob < 0.60:
            return f"Moderate tampering signals ({prob:.1%}). Artifacts: {art_str}."
        return f"High tampering probability ({prob:.1%}). Artifacts: {art_str}."

    def _recommendations(
        self, auth_score, report, blockchain, hash_match,
        cm_consistent, n_regions, context
    ) -> List[str]:
        recs = []

        if auth_score >= 80:
            recs.append("Content passes multi-layer forensic verification.")
        elif auth_score >= 55:
            recs.append("Content shows some anomalies — consider manual review.")
        elif auth_score >= 30:
            recs.append("Significant forensic signals detected. Verify with original creator.")
        else:
            recs.append("CRITICAL: Strong evidence of AI generation or tampering.")

        if context == "register":
            recs.append("Content registered on-chain — a timestamped ownership proof has been created.")
        elif not blockchain:
            recs.append("No blockchain record found — register to establish timestamped ownership.")

        if context == "verify" and not hash_match:
            recs.append("File hash does not match any registered record — may have been modified.")

        if cm_consistent is False:
            recs.append("Cross-modal inconsistency detected (e.g., audio/video mismatch). Possible deepfake.")

        baseline = {"image": 1, "video": 4, "audio": 2, "text": 1}.get(
            getattr(report, "modality", "unknown"), 2
        )
        excess = max(0, n_regions - baseline)
        if excess > 3:
            recs.append(f"{excess} tamper regions above baseline — review localization map.")

        artifacts = getattr(report, "artifacts", [])
        if "copy_move_region_detected" in artifacts:
            recs.append("Copy-move forgery detected — cloned regions identified in localization map.")
        if "tts_voice_clone_signature" in artifacts:
            recs.append("Audio exhibits TTS or voice-cloning frequency signature.")
        if "face_region_deepfake" in artifacts:
            recs.append("Face region shows deepfake indicators — frame-level localization provided.")

        return recs