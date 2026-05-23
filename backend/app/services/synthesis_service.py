from __future__ import annotations
import re
import hashlib
from typing import Optional, Any
from sqlalchemy.orm import Session
from openai import OpenAI

from app.core.config import settings
from app.services.hallucination_filter import HallucinationFilter, load_evidence_texts, CITATION_RE, PROPER_NOUN_RE, NUMERIC_RE, MONTHS

class SynthesisService:
    @staticmethod
    def compute_snapshot_hash(chunk_texts: dict[str, str]) -> str:
        """Computes a deterministic SHA-256 hash of the evidence chunk texts and IDs."""
        sorted_ids = sorted(chunk_texts.keys())
        hasher = hashlib.sha256()
        for cid in sorted_ids:
            hasher.update(cid.encode('utf-8'))
            hasher.update(chunk_texts[cid].encode('utf-8'))
        return hasher.hexdigest()

    @staticmethod
    def compute_citation_checksum(citations: list[tuple[str, str]]) -> str:
        """Computes a deterministic hash of the sorted citations in the response."""
        unique_cits = sorted(list(set(citations)))
        hasher = hashlib.sha256()
        for type_str, id_str in unique_cits:
            hasher.update(f"{type_str}:{id_str}".encode('utf-8'))
        return hasher.hexdigest()

    @staticmethod
    def calculate_synthesis_metrics(
        db: Session,
        tenant_id: int,
        response: str,
        evidence: dict,
        chunk_texts: dict[str, str]
    ) -> dict:
        """Calculates precise calibration and validation metrics for the generated response."""
        citations = CITATION_RE.findall(response)
        
        # 1. Evidence Snapshot Hash
        snapshot_hash = SynthesisService.compute_snapshot_hash(chunk_texts)
        
        # 2. Citation Checksum
        citation_checksum = SynthesisService.compute_citation_checksum(citations)
        
        # 3. Retrieval Coverage Score
        # Collect total chunk IDs retrieved
        retrieved_chunk_ids = list(chunk_texts.keys())
        total_chunks = len(retrieved_chunk_ids)
        
        # Determine chunk IDs cited in the response
        cited_chunk_ids = set()
        for type_str, id_str in citations:
            val_id = int(id_str)
            for thread_list in evidence.get('thread_evidence', {}).values():
                for r in thread_list:
                    payload = r.get('citation_payload', {})
                    if type_str == 'Email' and payload.get('email_id') == val_id:
                        cited_chunk_ids.add(r['chunk_id'])
                    if type_str == 'Attachment' and payload.get('attachment_id') == val_id:
                        cited_chunk_ids.add(r['chunk_id'])
            for att_list in evidence.get('attachment_evidence', {}).values():
                for r in att_list:
                    payload = r.get('citation_payload', {})
                    if type_str == 'Email' and payload.get('email_id') == val_id:
                        cited_chunk_ids.add(r['chunk_id'])
                    if type_str == 'Attachment' and payload.get('attachment_id') == val_id:
                        cited_chunk_ids.add(r['chunk_id'])

        coverage_score = len(cited_chunk_ids) / total_chunks if total_chunks > 0 else 0.0
        
        # 4. Citation Integrity Score
        ok_cit, _ = HallucinationFilter.verify_citation_mapping(response, evidence)
        citation_integrity = 1.0 if ok_cit else 0.0
        
        # 5. Unsupported Claim Risk Score
        clean_response = CITATION_RE.sub('', response)
        proper_nouns = PROPER_NOUN_RE.findall(clean_response)
        numbers = NUMERIC_RE.findall(clean_response)
        
        # Filter months from proper nouns
        filtered_proper_nouns = [p for p in proper_nouns if p.lower() not in MONTHS]
        
        combined_chunk_text = " ".join(chunk_texts.values()).lower()
        
        unverified_count = 0
        total_extracted_tokens = len(filtered_proper_nouns) + len(numbers)
        
        for ent in filtered_proper_nouns:
            if ent.lower() not in combined_chunk_text:
                unverified_count += 1
        for num in numbers:
            clean_num = num.strip('.,$ %')
            # Skip years
            if re.match(r'\b20\d{2}\b', clean_num):
                continue
            if clean_num and clean_num not in combined_chunk_text:
                unverified_count += 1
                
        claim_risk = unverified_count / total_extracted_tokens if total_extracted_tokens > 0 else 0.0
        
        return {
            'evidence_snapshot_hash': snapshot_hash,
            'citation_checksum': citation_checksum,
            'retrieval_coverage_score': coverage_score,
            'citation_integrity_score': citation_integrity,
            'unsupported_claim_risk': claim_risk
        }

    @staticmethod
    def prune_and_reanchor_evidence(query_text: str, chunk_texts: dict[str, str]) -> str:
        """Prunes evidence chunk text, keeping only sentences directly relevant to the user query."""
        pruned_sentences = []
        query_words = set(re.findall(r'\b\w+\b', query_text.lower()))
        
        for cid, text in chunk_texts.items():
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                sentence_words = set(re.findall(r'\b\w+\b', sentence.lower()))
                # Keep sentences that have word overlap with query keywords
                if sentence_words.intersection(query_words):
                    pruned_sentences.append(sentence.strip())
                    
        if not pruned_sentences:
            # Fallback to returning full texts if no direct overlap was found
            return "\n".join(chunk_texts.values())
        return "\n".join(pruned_sentences)

    @staticmethod
    def synthesize(
        db: Session,
        tenant_id: int,
        query_text: str,
        evidence: dict,
        correlation_id: str,
        max_retries: int = 2
    ) -> tuple[str, dict]:
        """Synthesizes an answer using low-variance, evidence-constrained generation and retry safety gates."""
        fallback_metrics = {
            'evidence_snapshot_hash': None,
            'citation_checksum': None,
            'retrieval_coverage_score': 0.0,
            'citation_integrity_score': 0.0,
            'unsupported_claim_risk': 1.0,
            'synthesis_validation_status': 'blocked_fallback'
        }

        # Validate base context presence
        if not evidence or evidence.get('evidence_count', 0) == 0:
            return "No matching email found.", {**fallback_metrics, 'synthesis_validation_status': 'no_evidence'}

        # Gather active chunk IDs
        chunk_ids = []
        for thread in evidence.get('thread_evidence', {}).values():
            for r in thread:
                chunk_ids.append(r['chunk_id'])
        for att in evidence.get('attachment_evidence', {}).values():
            for r in att:
                chunk_ids.append(r['chunk_id'])

        # Load authoritative raw texts
        chunk_texts = load_evidence_texts(db, tenant_id, chunk_ids)
        if not chunk_texts:
            return "Insufficient evidence available.", {**fallback_metrics, 'synthesis_validation_status': 'no_chunks_found'}

        # Format strict context formatting honoring thread and attachment boundaries
        evidence_str = ""
        
        # Format Thread evidence strictly separating boundaries
        for conv_id, thread in evidence.get('thread_evidence', {}).items():
            evidence_str += f"\n[MAILBOX SCOPE: BOUNDARY ENFORCED]\n--- CONVERSATION THREAD: {conv_id} ---\n"
            for r in thread:
                payload = r['citation_payload']
                email_id = payload.get('email_id')
                sender = payload.get('sender') or 'Unknown'
                recipient = payload.get('recipient') or 'Unknown'
                subject = payload.get('subject') or 'No Subject'
                timestamp = payload.get('source_timestamp') or 'No Date'
                chunk_text = chunk_texts.get(r['chunk_id'], '')
                
                evidence_str += (
                    f"[Email:{email_id}]\n"
                    f"From: {sender}\n"
                    f"To: {recipient}\n"
                    f"Subject: {subject}\n"
                    f"Date: {timestamp}\n"
                    f"Content:\n{chunk_text}\n"
                    f"--------------------\n"
                )

        # Format Attachment evidence
        for att_id, att_list in evidence.get('attachment_evidence', {}).items():
            if att_id == 'none':
                continue
            evidence_str += f"\n[ATTACHMENT SCOPE: BOUNDARY ENFORCED]\n--- ATTACHMENT: {att_id} ---\n"
            for r in att_list:
                payload = r['citation_payload']
                email_id = payload.get('email_id')
                filename = payload.get('filename') or 'Unknown File'
                chunk_text = chunk_texts.get(r['chunk_id'], '')
                
                evidence_str += (
                    f"[Attachment:{att_id}] (Attached to Email:{email_id})\n"
                    f"Filename: {filename}\n"
                    f"Content:\n{chunk_text}\n"
                    f"--------------------\n"
                )

        # Prompts for low-variance generation
        system_instruction = (
            "You are Veteran AI, a precise multi-tenant Outlook semantic intelligence engine.\n"
            "Your task is to synthesize a factual, grounded response to the user's query based ONLY on the retrieved email communications and attachments provided.\n"
            "Every single claim, factual assertion, or reference you make MUST be directly supported by a source from the communications.\n"
            "You MUST inject explicit inline citations in the format `[Email:<id>]` or `[Attachment:<id>]` immediately after the claim.\n"
            "Example: \"John agreed to the contract terms on May 12 [Email:101], and sent the signed document [Attachment:201].\"\n"
            "Do not invent proper nouns, names, numbers, dates, or details that are not in the text. Ensure any year or month mention in your response matches the timestamps of the cited emails.\n"
            "If you cannot answer the query using the provided context, or if the context is insufficient, you must respond EXACTLY with one of these safe fallback statements:\n"
            "- If no communications match: \"No matching email found.\"\n"
            "- If context is insufficient to answer: \"Insufficient evidence available.\"\n"
            "- If dates or details are ambiguous: \"Unable to verify from indexed communications.\""
        )

        user_content = (
            f"=== RETRIEVED COMMUNICATIONS ===\n"
            f"{evidence_str}\n"
            f"=== END OF COMMUNICATIONS ===\n\n"
            f"USER QUERY: {query_text}"
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        current_attempt = 0
        validation_status = 'validated'

        while current_attempt <= max_retries:
            try:
                # If we are in a retry, we trigger the evidence-first re-anchoring pruning
                if current_attempt > 0:
                    validation_status = 'regenerated'
                    # Re-anchor the context on strictly matching sentences
                    pruned_evidence = SynthesisService.prune_and_reanchor_evidence(query_text, chunk_texts)
                    
                    reanchored_user_content = (
                        f"=== VERIFIED EVIDENCE ONLY: STRICTLY CONSTRAINED ===\n"
                        f"{pruned_evidence}\n"
                        f"=== END OF EVIDENCE ===\n\n"
                        f"CRITICAL REQUIREMENT:\n"
                        f"Your previous response failed our strict grounding filters. We have pruned the evidence to ONLY verified facts matching the query.\n"
                        f"Synthesize your response relying EXCLUSIVELY on these verified sentences. Do not introduce any external terms, names, or numbers.\n"
                        f"USER QUERY: {query_text}"
                    )
                    messages = [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": reanchored_user_content}
                    ]

                # Constrained Low-Variance Synthesis
                completion = client.chat.completions.create(
                    model=settings.SYNTHESIS_MODEL,
                    messages=messages,
                    temperature=0.0  # Zero temperature for minimum variance
                )

                response_text = completion.choices[0].message.content.strip()

                # Bypass filter for standard safety fallback messages
                safe_fallbacks = [
                    "No matching email found.",
                    "Insufficient evidence available.",
                    "Unable to verify from indexed communications."
                ]
                if response_text in safe_fallbacks:
                    metrics = SynthesisService.calculate_synthesis_metrics(db, tenant_id, response_text, evidence, chunk_texts)
                    return response_text, {**metrics, 'synthesis_validation_status': 'validated'}

                # Run response through the Hallucination Filter safety gate
                ok, filtered_response = HallucinationFilter.verify_response_gate(
                    db, tenant_id, response_text, evidence
                )

                if ok:
                    # Success: Calculate and return with full metadata block
                    metrics = SynthesisService.calculate_synthesis_metrics(db, tenant_id, filtered_response, evidence, chunk_texts)
                    return filtered_response, {**metrics, 'synthesis_validation_status': validation_status}
                else:
                    # In case of filter blockages, trigger the re-anchoring pipeline in next attempt
                    current_attempt += 1

            except Exception as e:
                # API error or unexpected exception returns safe fallback
                return "Unable to verify from indexed communications.", {**fallback_metrics, 'synthesis_validation_status': 'api_error'}

        # Exhausted retries -> Abort and return safe fallback based on filter validation failures
        ok_cit, _ = HallucinationFilter.verify_citation_mapping(response_text, evidence)
        final_fallback = "Insufficient evidence available." if not ok_cit else "Unable to verify from indexed communications."
        return final_fallback, {**fallback_metrics, 'synthesis_validation_status': 'blocked_fallback'}
