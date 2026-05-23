import json
from app.services.retrieval_rerank import rerank_hits
from app.services.retrieval_confidence import compute_confidence

# Define a gold standard annotated dataset representing expected retrieval targets for specific queries
GOLD_STANDARD_DATASET = [
    {
        "query": "Project Helios budget approval",
        "expected_email_ids": [101, 102],
        "expected_attachment_ids": [201],
        "simulated_hits": [
            {"id": "v1", "score": 0.85, "payload": {"chunk_id": "c1", "email_id": 101, "mailbox_id": 1, "conversation_id": "t1", "attachment_id": None, "source_timestamp": "2026-05-12T10:00:00", "source_start_offset": 0, "source_end_offset": 100}},
            {"id": "v2", "score": 0.75, "payload": {"chunk_id": "c2", "email_id": 102, "mailbox_id": 1, "conversation_id": "t1", "attachment_id": None, "source_timestamp": "2026-05-12T10:05:00", "source_start_offset": 0, "source_end_offset": 100}},
            {"id": "v3", "score": 0.80, "payload": {"chunk_id": "c3", "email_id": 102, "mailbox_id": 1, "conversation_id": "t1", "attachment_id": 201, "source_timestamp": "2026-05-12T10:10:00", "source_start_offset": 0, "source_end_offset": 100}},
            {"id": "v4", "score": 0.40, "payload": {"chunk_id": "c4", "email_id": 103, "mailbox_id": 1, "conversation_id": "t2", "attachment_id": None, "source_timestamp": "2026-05-13T10:00:00", "source_start_offset": 0, "source_end_offset": 100}}, # Irrelevant
        ]
    },
    {
        "query": "Timeline revision for Acme contract",
        "expected_email_ids": [105],
        "expected_attachment_ids": [],
        "simulated_hits": [
            {"id": "v5", "score": 0.90, "payload": {"chunk_id": "c5", "email_id": 105, "mailbox_id": 1, "conversation_id": "t3", "attachment_id": None, "source_timestamp": "2026-05-14T09:00:00", "source_start_offset": 0, "source_end_offset": 100}},
            {"id": "v6", "score": 0.30, "payload": {"chunk_id": "c6", "email_id": 106, "mailbox_id": 1, "conversation_id": "t4", "attachment_id": None, "source_timestamp": "2026-05-15T09:00:00", "source_start_offset": 0, "source_end_offset": 100}}, # Irrelevant
        ]
    },
    {
        "query": "Beta team onboarding guidelines",
        "expected_email_ids": [110, 111],
        "expected_attachment_ids": [205],
        "simulated_hits": [
            {"id": "v7", "score": 0.35, "payload": {"chunk_id": "c7", "email_id": 109, "mailbox_id": 1, "conversation_id": "t5", "attachment_id": None, "source_timestamp": "2026-05-16T08:00:00", "source_start_offset": 0, "source_end_offset": 100}}, # Irrelevant
            {"id": "v8", "score": 0.88, "payload": {"chunk_id": "c8", "email_id": 110, "mailbox_id": 1, "conversation_id": "t6", "attachment_id": None, "source_timestamp": "2026-05-16T08:30:00", "source_start_offset": 0, "source_end_offset": 100}},
            {"id": "v9", "score": 0.82, "payload": {"chunk_id": "c9", "email_id": 111, "mailbox_id": 1, "conversation_id": "t6", "attachment_id": 205, "source_timestamp": "2026-05-16T09:00:00", "source_start_offset": 0, "source_end_offset": 100}},
        ]
    }
]

def run_retrieval_benchmark():
    print("====================================================")
    print("VETERAN RETRIEVAL CORRECTNESS BENCHMARKING FRAMEWORK")
    print("====================================================")
    
    total_queries = len(GOLD_STANDARD_DATASET)
    avg_precision_at_3 = 0.0
    avg_recall_at_3 = 0.0
    reciprocal_ranks = []
    average_precisions = []

    for idx, case in enumerate(GOLD_STANDARD_DATASET):
        query = case["query"]
        expected_emails = set(case["expected_email_ids"])
        expected_attachments = set(case["expected_attachment_ids"])
        
        # Simulate retrieval search hits
        hits = case["simulated_hits"]
        
        # Run through the active reranking logic
        reranked = rerank_hits(hits, filters={})
        
        # We evaluate at K = 3
        k = 3
        top_k_results = reranked[:k]
        
        retrieved_relevant = 0
        relevant_rank = None
        precisions = []
        
        for rank, r in enumerate(top_k_results):
            payload = r["payload"]
            eid = payload.get("email_id")
            aid = payload.get("attachment_id")
            
            is_relevant = (eid in expected_emails) or (aid is not None and aid in expected_attachments)
            if is_relevant:
                retrieved_relevant += 1
                if relevant_rank is None:
                    relevant_rank = rank + 1
                # Calculate precision at this point
                precisions.append(retrieved_relevant / (rank + 1))
        
        # Precision@K
        precision_at_k = retrieved_relevant / k
        avg_precision_at_3 += precision_at_k
        
        # Recall@K
        total_relevant = len(expected_emails) + len(expected_attachments)
        recall_at_k = retrieved_relevant / total_relevant if total_relevant > 0 else 0.0
        avg_recall_at_3 += recall_at_k
        
        # MRR component
        mrr_val = 1.0 / relevant_rank if relevant_rank is not None else 0.0
        reciprocal_ranks.append(mrr_val)
        
        # Average Precision for MAP
        ap = sum(precisions) / total_relevant if precisions and total_relevant > 0 else 0.0
        average_precisions.append(ap)
        
        print(f"Query {idx + 1}: '{query}'")
        print(f"  - Precision@3: {precision_at_k:.4f}")
        print(f"  - Recall@3:    {recall_at_k:.4f}")
        print(f"  - First Match Rank: {relevant_rank if relevant_rank else 'N/A'}")
        print(f"  - Average Precision: {ap:.4f}")
        
        # Calibration printout based on computed confidence scores
        for r in top_k_results:
            payload = r["payload"]
            conf = compute_confidence(
                vector_score=r["score"],
                rerank_score=r["rerank_score"],
                citation_integrity=1.0,
                evidence_density=1.0
            )
            print(f"    * Chunk {payload['chunk_id']} -> Rerank Score: {r['rerank_score']:.4f}, Calibrated Confidence: {conf['evidence_confidence']:.4f}")
        print("-" * 52)

    map_val = sum(average_precisions) / total_queries
    mrr_val = sum(reciprocal_ranks) / total_queries
    mean_p_at_k = avg_precision_at_3 / total_queries
    mean_r_at_k = avg_recall_at_3 / total_queries

    print("OVERALL PERFORMANCE SUMMARY:")
    print(f"  * Mean Precision@3: {mean_p_at_k:.4f}")
    print(f"  * Mean Recall@3:    {mean_r_at_k:.4f}")
    print(f"  * MAP (Mean Average Precision): {map_val:.4f}")
    print(f"  * MRR (Mean Reciprocal Rank):    {mrr_val:.4f}")
    print("====================================================")
    
    # Assert benchmark thresholds
    assert map_val >= 0.85, f"MAP score {map_val:.4f} did not meet required production safety threshold of 0.85"
    assert mrr_val >= 0.85, f"MRR score {mrr_val:.4f} did not meet required production safety threshold of 0.85"
    print("BENCHMARKING SUCCESSFUL: All quality gates passed cleanly.")

if __name__ == "__main__":
    run_retrieval_benchmark()
