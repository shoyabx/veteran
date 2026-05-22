from __future__ import annotations


def compute_confidence(vector_score: float, rerank_score: float, citation_integrity: float, evidence_density: float) -> dict:
    retrieval_conf = max(0.0, min(1.0, (0.6 * vector_score) + (0.4 * rerank_score)))
    evidence_conf = max(0.0, min(1.0, (0.5 * retrieval_conf) + (0.3 * citation_integrity) + (0.2 * evidence_density)))
    return {
        'retrieval_confidence': retrieval_conf,
        'evidence_confidence': evidence_conf,
        'citation_integrity_score': citation_integrity,
    }
