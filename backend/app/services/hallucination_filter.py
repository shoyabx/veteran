from __future__ import annotations
import re
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.indexing import IndexedChunk, AttachmentChunk
from app.models.ingestion import Attachment

# Patterns for citation matching (e.g. [Email:12] or [Attachment:34])
CITATION_RE = re.compile(r'\[(Email|Attachment):(\d+)\]')

# Standard entity proper-noun extractor and number extractor
PROPER_NOUN_RE = re.compile(r'\b[A-Z][a-zA-Z0-9_-]{2,}\b')
NUMERIC_RE = re.compile(r'\b\$?\d+(?:[.,]\d+)?%?\b')
YEAR_RE = re.compile(r'\b20\d{2}\b')

MONTHS = {
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
}


def load_evidence_texts(db: Session, tenant_id: int, chunk_ids: list[str]) -> dict[str, str]:
    """Retrieves authoritative raw chunk texts from SQL database by chunk_ids."""
    if not chunk_ids:
        return {}
    chunks = db.scalars(
        select(IndexedChunk).where(
            IndexedChunk.tenant_id == tenant_id,
            IndexedChunk.chunk_id.in_(chunk_ids)
        )
    ).all()
    out = {c.chunk_id: c.chunk_text for c in chunks}

    missing = [cid for cid in chunk_ids if cid not in out]
    if missing:
        att_chunks = db.scalars(
            select(AttachmentChunk).where(
                AttachmentChunk.tenant_id == tenant_id,
                AttachmentChunk.chunk_id.in_(missing)
            )
        ).all()
        for ac in att_chunks:
            out[ac.chunk_id] = ac.chunk_text
    return out


class HallucinationFilter:
    @staticmethod
    def verify_citation_mapping(response: str, evidence: dict) -> tuple[bool, str | None]:
        """Ensures all citations in response map strictly to active records in evidence."""
        citations = CITATION_RE.findall(response)
        if not citations:
            # If the response makes claims but includes no citations, it is unsupported
            return False, 'no_citations_provided'

        valid_emails = set()
        valid_attachments = set()

        for thread_list in evidence.get('thread_evidence', {}).values():
            for r in thread_list:
                payload = r.get('citation_payload', {})
                if payload.get('email_id') is not None:
                    valid_emails.add(int(payload['email_id']))
                if payload.get('attachment_id') is not None:
                    valid_attachments.add(int(payload['attachment_id']))

        for att_list in evidence.get('attachment_evidence', {}).values():
            for r in att_list:
                payload = r.get('citation_payload', {})
                if payload.get('email_id') is not None:
                    valid_emails.add(int(payload['email_id']))
                if payload.get('attachment_id') is not None:
                    valid_attachments.add(int(payload['attachment_id']))

        for type_str, id_str in citations:
            val_id = int(id_str)
            if type_str == 'Email' and val_id not in valid_emails:
                return False, f'orphan_citation:Email:{val_id}'
            if type_str == 'Attachment' and val_id not in valid_attachments:
                return False, f'orphan_citation:Attachment:{val_id}'

        return True, None

    @staticmethod
    def verify_numeric_and_entity_fidelity(
        db: Session,
        tenant_id: int,
        response: str,
        evidence: dict
    ) -> tuple[bool, str | None]:
        """Asserts all proper noun entities and numbers in response appear in cited chunks."""
        citations = CITATION_RE.findall(response)
        if not citations:
            return False, 'no_citations_provided'

        # Map citation ids to chunk IDs from evidence
        citation_chunk_ids = []
        for type_str, id_str in citations:
            val_id = int(id_str)
            
            # Find matching chunks in evidence
            for thread_list in evidence.get('thread_evidence', {}).values():
                for r in thread_list:
                    payload = r.get('citation_payload', {})
                    if type_str == 'Email' and payload.get('email_id') == val_id:
                        citation_chunk_ids.append(payload['chunk_id'])
                    if type_str == 'Attachment' and payload.get('attachment_id') == val_id:
                        citation_chunk_ids.append(payload['chunk_id'])

            for att_list in evidence.get('attachment_evidence', {}).values():
                for r in att_list:
                    payload = r.get('citation_payload', {})
                    if type_str == 'Email' and payload.get('email_id') == val_id:
                        citation_chunk_ids.append(payload['chunk_id'])
                    if type_str == 'Attachment' and payload.get('attachment_id') == val_id:
                        citation_chunk_ids.append(payload['chunk_id'])

        chunk_texts = load_evidence_texts(db, tenant_id, citation_chunk_ids)
        combined_chunk_text = " ".join(chunk_texts.values())

        # Strip citation markup from the response text before extracting numbers and entities
        clean_response = CITATION_RE.sub('', response)

        # 1. Verify numbers (amounts, dates, currencies, percents)
        numbers = NUMERIC_RE.findall(clean_response)
        for num in numbers:
            # We strip trailing/leading spaces or punctuation if any
            clean_num = num.strip('.,$ %')
            # Skip years as they are already validated by the timeline checker
            if YEAR_RE.match(clean_num):
                continue
            if clean_num and clean_num not in combined_chunk_text:
                return False, f'fabricated_number:{num}'

        # 2. Verify proper noun entities
        entities = PROPER_NOUN_RE.findall(clean_response)
        for ent in entities:
            # Skip month names as they are already validated by the timeline checker
            if ent.lower() in MONTHS:
                continue
            if ent.lower() not in combined_chunk_text.lower():
                return False, f'fabricated_entity:{ent}'

        return True, None

    @staticmethod
    def verify_timeline_consistency(
        response: str,
        evidence: dict
    ) -> tuple[bool, str | None]:
        """Ensures years and months in response match cited emails timestamps or context."""
        citations = CITATION_RE.findall(response)
        if not citations:
            return False, 'no_citations_provided'

        # Collect cited email received/sent dates
        cited_dates = []
        for type_str, id_str in citations:
            val_id = int(id_str)
            for thread_list in evidence.get('thread_evidence', {}).values():
                for r in thread_list:
                    payload = r.get('citation_payload', {})
                    if payload.get('source_timestamp') and (
                        (type_str == 'Email' and payload.get('email_id') == val_id) or
                        (type_str == 'Attachment' and payload.get('attachment_id') == val_id)
                    ):
                        cited_dates.append(payload['source_timestamp'])

        # Check for years (e.g. 2024, 2025)
        response_years = YEAR_RE.findall(response)
        for yr in response_years:
            year_matched = False
            for dt_str in cited_dates:
                if yr in dt_str:
                    year_matched = True
                    break
            if not year_matched:
                return False, f'timeline_year_mismatch:{yr}'

        # Check for month mentions
        words = re.findall(r'\b[a-zA-Z]+\b', response.lower())
        response_months = [w for w in words if w in MONTHS]
        for mon in response_months:
            month_matched = False
            # Check if matching any email timestamp month component
            for dt_str in cited_dates:
                # dt_str format is standard ISO string: e.g. "2024-05-12T..."
                # Extract month number (index 5-7) and check if it aligns with month name
                try:
                    month_num = int(dt_str.split('-')[1])
                    month_names_map = {
                        1: ('january', 'jan'), 2: ('february', 'feb'), 3: ('march', 'mar'),
                        4: ('april', 'apr'), 5: ('may',), 6: ('june', 'jun'),
                        7: ('july', 'jul'), 8: ('august', 'aug'), 9: ('september', 'sep'),
                        10: ('october', 'oct'), 11: ('november', 'nov'), 12: ('december', 'dec')
                    }
                    if mon in month_names_map.get(month_num, ()):
                        month_matched = True
                        break
                except (IndexError, ValueError):
                    continue
            if not month_matched:
                return False, f'timeline_month_mismatch:{mon}'

        return True, None

    @classmethod
    def verify_response_gate(
        cls,
        db: Session,
        tenant_id: int,
        response: str,
        evidence: dict
    ) -> tuple[bool, str]:
        """Intercepts response, runs all safety filters, and routes safe fallback if blocked."""
        # 1. Verify Citation Grounding
        ok, err = cls.verify_citation_mapping(response, evidence)
        if not ok:
            return False, "Insufficient evidence available."

        # 2. Verify Entity & Numeric Fidelity
        ok, err = cls.verify_numeric_and_entity_fidelity(db, tenant_id, response, evidence)
        if not ok:
            return False, "Unable to verify from indexed communications."

        # 3. Verify Timeline Consistency
        ok, err = cls.verify_timeline_consistency(response, evidence)
        if not ok:
            return False, "Unable to verify from indexed communications."

        return True, response
