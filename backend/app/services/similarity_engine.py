"""
SIF Sentinel — Recurring-Risk & Semantic Similarity Engine (Phase 11)
=====================================================================

Implements semantic similarity search, nearest-neighbor matching, and cross-report
recurring-risk pattern detection using Sentence Transformers (all-MiniLM-L6-v2).

Does NOT rely on keyword matching. Uses continuous 384-dimensional vector cosine similarity
to discover systemic hazards and defense failure patterns.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional
import numpy as np

from app.schemas.api_v1 import (
    SemanticRecurringPattern,
    SimilarReportItem,
    TemporalTrend,
)
from app.schemas.decision import PriorityLevel
from app.services.embedding_service import SemanticEmbeddingService, get_embedding_service

logger = logging.getLogger("sif_sentinel.similarity_engine")


class RecurringRiskEngine:
    """
    Manages dense vector storage and performs semantic similarity analysis,
    nearest-neighbor retrieval, and recurring precursor pattern detection.
    """

    def __init__(self, embedding_service: Optional[SemanticEmbeddingService] = None):
        self.embedding_service = embedding_service or get_embedding_service()
        self._lock = threading.RLock()
        # In-memory vector registry: report_id -> np.ndarray (384,)
        self._vectors: dict[str, np.ndarray] = {}

    def index_report(
        self, report_id: str, text: str, vector: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute (or register) a dense semantic embedding for an analyzed report.
        """
        with self._lock:
            if vector is not None:
                vec = vector.astype(np.float32)
            else:
                vec = self.embedding_service.get_embedding(text)
            self._vectors[report_id] = vec
            return vec

    def index_batch(self, report_tuples: list[tuple[str, str]]) -> int:
        """
        Batch index (report_id, text) pairs.
        """
        if not report_tuples:
            return 0

        ids = [t[0] for t in report_tuples]
        texts = [t[1] for t in report_tuples]
        vectors = self.embedding_service.get_embeddings_batch(texts)

        with self._lock:
            for rep_id, vec in zip(ids, vectors):
                self._vectors[rep_id] = vec
            return len(ids)

    def get_vector(self, report_id: str) -> Optional[np.ndarray]:
        """Fetch the stored 384-dim vector for a report."""
        with self._lock:
            return self._vectors.get(report_id)

    def find_similar_reports(
        self,
        report_id: str,
        stored_reports: dict[str, Any],
        limit: int = 5,
        threshold: float = 0.5,
    ) -> list[SimilarReportItem]:
        """
        Find semantically similar reports to a given target report using vector cosine similarity.
        Filters out self-matches and applies similarity threshold.
        """
        with self._lock:
            target_vec = self._vectors.get(report_id)
            target_report = stored_reports.get(report_id)

            # If vector not yet cached but report exists, generate vector on the fly
            if target_vec is None and target_report is not None:
                text = getattr(target_report, "report_text", "")
                if text:
                    target_vec = self.index_report(report_id, text)

            if target_vec is None:
                return []

            candidates: list[tuple[str, float]] = []

            for other_id, other_vec in self._vectors.items():
                if other_id == report_id:
                    continue  # Exclude self

                sim = self.embedding_service.compute_similarity(target_vec, other_vec)
                if sim >= threshold:
                    candidates.append((other_id, sim))

            # Sort descending by similarity score
            candidates.sort(key=lambda item: item[1], reverse=True)
            top_candidates = candidates[:limit]

            results: list[SimilarReportItem] = []
            for other_id, sim_score in top_candidates:
                report_obj = stored_reports.get(other_id)
                if not report_obj:
                    continue

                analysis = getattr(report_obj, "analysis", None)
                priority = getattr(report_obj, "final_priority", None)
                if not priority and analysis:
                    priority = getattr(analysis, "priority", PriorityLevel.LOW)

                act = getattr(analysis, "activity", None) if analysis else None
                haz = getattr(analysis, "hazard", None) if analysis else None
                bar = getattr(analysis, "barrier", None) if analysis else None
                bstat = getattr(analysis, "barrier_status", None) if analysis else None
                created = getattr(report_obj, "created_at", None)
                text = getattr(report_obj, "report_text", "")

                results.append(
                    SimilarReportItem(
                        report_id=other_id,
                        similarity_score=float(sim_score),
                        report_text=text,
                        priority=priority or PriorityLevel.LOW,
                        activity=act,
                        hazard=haz,
                        barrier=bar,
                        barrier_status=bstat,
                        created_at=created,
                    )
                )

            return results

    def detect_recurring_patterns(
        self,
        stored_reports: list[Any],
        similarity_threshold: float = 0.60,
        min_cluster_size: int = 2,
    ) -> list[SemanticRecurringPattern]:
        """
        Group reports into semantic risk clusters using dense vector cosine similarity.
        Calculates:
          - pattern ID
          - number of reports
          - common activity
          - common hazard
          - common barrier failure
          - temporal date trend (direction, first_seen, last_seen, span_days)
          - representative medoid text
          - intra-cluster average similarity
          - recommended mitigation action
        """
        with self._lock:
            # Filter reports with valid vector representations
            valid_reports = []
            for r in stored_reports:
                rep_id = getattr(r, "report_id", "")
                vec = self._vectors.get(rep_id)
                if vec is None:
                    # Index if missing
                    txt = getattr(r, "report_text", "")
                    if txt:
                        vec = self.index_report(rep_id, txt)
                if vec is not None:
                    valid_reports.append(r)

            n = len(valid_reports)
            if n < min_cluster_size:
                return []

            # 1. Build vector matrix and pairwise similarity
            vectors = np.array([self._vectors[r.report_id] for r in valid_reports], dtype=np.float32)
            sim_matrix = self.embedding_service.compute_similarity_matrix(vectors)

            # 2. Graph Connected Components / Semantic Proximity Clustering
            # Reports with similarity >= threshold share a semantic edge
            visited = [False] * n
            raw_clusters: list[list[int]] = []

            for i in range(n):
                if visited[i]:
                    continue

                cluster = []
                queue = [i]
                visited[i] = True

                while queue:
                    curr = queue.pop(0)
                    cluster.append(curr)

                    # Find all unvisited neighbors with semantic similarity >= threshold
                    for j in range(n):
                        if not visited[j] and sim_matrix[curr, j] >= similarity_threshold:
                            visited[j] = True
                            queue.append(j)

                if len(cluster) >= min_cluster_size:
                    raw_clusters.append(cluster)

            # Sort clusters by size descending
            raw_clusters.sort(key=lambda c: len(c), reverse=True)

            # 3. Construct SemanticRecurringPattern for each cluster
            patterns: list[SemanticRecurringPattern] = []

            for idx, cluster_indices in enumerate(raw_clusters):
                cluster_reports = [valid_reports[i] for i in cluster_indices]
                report_ids = [r.report_id for r in cluster_reports]
                cluster_vectors = vectors[cluster_indices]

                # Intra-cluster average pairwise similarity
                sub_matrix = sim_matrix[np.ix_(cluster_indices, cluster_indices)]
                if len(cluster_indices) > 1:
                    # Exclude diagonal
                    mask = ~np.eye(len(cluster_indices), dtype=bool)
                    avg_sim = float(np.mean(sub_matrix[mask]))
                else:
                    avg_sim = 1.0

                # Medoid report (highest sum of similarity to other cluster members)
                sim_sums = np.sum(sub_matrix, axis=1)
                medoid_idx = cluster_indices[int(np.argmax(sim_sums))]
                medoid_report = valid_reports[medoid_idx]
                medoid_text = getattr(medoid_report, "report_text", "")

                # Common activity
                activities = [
                    getattr(r.analysis, "activity", None)
                    for r in cluster_reports
                    if getattr(r, "analysis", None) and r.analysis.activity
                ]
                common_act = (
                    Counter(activities).most_common(1)[0][0]
                    if activities
                    else "High-Energy Operations"
                )

                # Common hazard
                hazards = [
                    getattr(r.analysis, "hazard", None)
                    for r in cluster_reports
                    if getattr(r, "analysis", None) and r.analysis.hazard
                ]
                common_haz = (
                    Counter(hazards).most_common(1)[0][0]
                    if hazards
                    else "Physical Energy"
                )

                # Common barrier failure
                barrier_failures = []
                for r in cluster_reports:
                    if getattr(r, "analysis", None) and r.analysis.barrier:
                        b_stat = r.analysis.barrier_status or "Compromised"
                        barrier_failures.append(f"{r.analysis.barrier} ({b_stat})")

                common_bar = (
                    Counter(barrier_failures).most_common(1)[0][0]
                    if barrier_failures
                    else "Control Verification Deficient"
                )

                # Temporal trend analysis
                trend = self._analyze_temporal_trend(cluster_reports)

                # Prescriptive safety mitigation recommendation
                recommendation = self._generate_recommendation(common_haz, common_bar, common_act)

                pat_id = f"PAT-SEM-{idx + 1:03d}"
                patterns.append(
                    SemanticRecurringPattern(
                        pattern_id=pat_id,
                        number_of_reports=len(cluster_reports),
                        report_ids=report_ids,
                        common_activity=common_act,
                        common_hazard=common_haz,
                        common_barrier_failure=common_bar,
                        trend=trend,
                        representative_text=medoid_text,
                        average_similarity=round(max(0.0, min(1.0, avg_sim)), 4),
                        recommended_action=recommendation,
                    )
                )

            return patterns

    def _analyze_temporal_trend(self, reports: list[Any]) -> TemporalTrend:
        """
        Analyze date progression and calculate trend metrics for a group of reports.
        """
        dates: list[datetime] = []
        date_counts: Counter[str] = Counter()

        for r in reports:
            dt = getattr(r, "created_at", None)
            if isinstance(dt, datetime):
                dates.append(dt)
                date_counts[dt.strftime("%Y-%m-%d")] += 1

        if not dates:
            return TemporalTrend(
                trend_direction="stable",
                first_seen=None,
                last_seen=None,
                span_days=0,
                date_counts={},
            )

        dates.sort()
        first_dt = dates[0]
        last_dt = dates[-1]
        span_days = max(0, (last_dt - first_dt).days)

        # Determine trend direction
        if len(dates) <= 2 or span_days == 0:
            direction = "isolated"
        else:
            # Split time window into two halves
            mid_time = first_dt.timestamp() + (last_dt.timestamp() - first_dt.timestamp()) / 2.0
            first_half = sum(1 for d in dates if d.timestamp() <= mid_time)
            second_half = sum(1 for d in dates if d.timestamp() > mid_time)

            if second_half > first_half:
                direction = "increasing"
            elif second_half < first_half:
                direction = "decreasing"
            else:
                direction = "stable"

        return TemporalTrend(
            trend_direction=direction,
            first_seen=first_dt,
            last_seen=last_dt,
            span_days=span_days,
            date_counts=dict(date_counts),
        )

    def _generate_recommendation(
        self, hazard: str, barrier_failure: str, activity: str
    ) -> str:
        """Synthesize actionable prescriptive safety guidance for a semantic precursor cluster."""
        haz_lower = hazard.lower()
        bar_lower = barrier_failure.lower()

        if "electric" in haz_lower or "isolation" in bar_lower:
            return "Mandate immediate verification of Lockout/Tagout (LOTO) zero-energy isolation procedures and audit electrical permit compliance across all operating units."
        elif "gas" in haz_lower or "confined" in bar_lower or "toxic" in haz_lower:
            return "Issue immediate site safety bulletin requiring continuous 4-gas atmospheric monitoring and dedicated standby observers for all confined vessel entries."
        elif "height" in haz_lower or "fall" in bar_lower:
            return "Initiate comprehensive inspection of scaffolding tags, 100% tie-off compliance, and harness inspection logs prior to work at elevation."
        elif "struck" in haz_lower or "rigging" in bar_lower or "lifting" in haz_lower:
            return "Establish physical exclusion zone barriers around active crane swings and verify lifting supervisor sign-offs on all rigging plans."
        else:
            return f"Initiate targeted HSE operational audit for {activity} focusing on {barrier_failure} to eliminate recurring precursor vulnerability."

    def calculate_recurrence_signal(
        self, text: str, high_risk_reports: list[Any]
    ) -> float:
        """
        Calculate recurrence signal (0.0 to 1.0) for a new report against known high-risk precursors.
        Feeds into Phase 7 multi-factor prioritization engine.
        """
        with self._lock:
            if not high_risk_reports:
                return 0.0

            query_vec = self.embedding_service.get_embedding(text)
            max_sim = 0.0

            for r in high_risk_reports:
                rep_id = getattr(r, "report_id", "")
                r_vec = self._vectors.get(rep_id)
                if r_vec is None:
                    txt = getattr(r, "report_text", "")
                    if txt:
                        r_vec = self.index_report(rep_id, txt)
                if r_vec is not None:
                    sim = self.embedding_service.compute_similarity(query_vec, r_vec)
                    if sim > max_sim:
                        max_sim = sim

            # Rescale similarity: anything above 0.35 indicates semantic recurrence
            if max_sim >= 0.70:
                return 1.0
            elif max_sim >= 0.35:
                return round((max_sim - 0.35) / 0.35, 3)
            return 0.0


# Global singleton
_similarity_engine_instance: Optional[RecurringRiskEngine] = None


def get_similarity_engine() -> RecurringRiskEngine:
    """Retrieve global singleton RecurringRiskEngine."""
    global _similarity_engine_instance
    if _similarity_engine_instance is None:
        _similarity_engine_instance = RecurringRiskEngine()
    return _similarity_engine_instance
