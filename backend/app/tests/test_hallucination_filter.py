import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.indexing import IndexedChunk, AttachmentChunk
from app.services.hallucination_filter import HallucinationFilter


@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    # Create only the tables required for this test, avoiding SQLite JSONB compilation issues
    IndexedChunk.__table__.create(bind=engine)
    AttachmentChunk.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_verify_citation_mapping_success():
    evidence = {
        'thread_evidence': {
            'conv_1': [
                {'citation_payload': {'email_id': 101, 'chunk_id': 'c1'}},
                {'citation_payload': {'email_id': 102, 'chunk_id': 'c2'}}
            ]
        },
        'attachment_evidence': {
            'att_1': [
                {'citation_payload': {'attachment_id': 201, 'email_id': 102, 'chunk_id': 'c3'}}
            ]
        }
    }

    # Citations exactly match available IDs in evidence
    response = "The contract terms were approved in [Email:101] and detailed in [Attachment:201]."
    ok, err = HallucinationFilter.verify_citation_mapping(response, evidence)
    assert ok
    assert err is None


def test_verify_citation_mapping_failures():
    evidence = {
        'thread_evidence': {
            'conv_1': [
                {'citation_payload': {'email_id': 101, 'chunk_id': 'c1'}}
            ]
        },
        'attachment_evidence': {}
    }

    # 1. No citations provided
    r1 = "The contract terms were approved."
    ok1, err1 = HallucinationFilter.verify_citation_mapping(r1, evidence)
    assert not ok1
    assert err1 == 'no_citations_provided'

    # 2. Orphan Email Citation
    r2 = "Approved in [Email:102]."
    ok2, err2 = HallucinationFilter.verify_citation_mapping(r2, evidence)
    assert not ok2
    assert 'orphan_citation:Email:102' in err2

    # 3. Orphan Attachment Citation
    r3 = "Approved in [Attachment:201]."
    ok3, err3 = HallucinationFilter.verify_citation_mapping(r3, evidence)
    assert not ok3
    assert 'orphan_citation:Attachment:201' in err3


def test_verify_numeric_and_entity_fidelity(db_session):
    # Seed mock chunks in database
    db_session.add(IndexedChunk(
        tenant_id=1, user_id=1, mailbox_id=1, email_id=101,
        chunk_id='c1', chunk_text="We agreed on a budget of $50,000 for Project Helios.",
        chunk_checksum="sum1", source_start_offset=0, source_end_offset=50,
        token_count=10, vector_id="vec1", content_version=1, semantic_version="2.1"
    ))
    db_session.commit()

    evidence = {
        'thread_evidence': {
            'conv_1': [
                {'citation_payload': {'email_id': 101, 'chunk_id': 'c1'}}
            ]
        },
        'attachment_evidence': {}
    }

    # 1. SUCCESS: Proper Nouns (Project, Helios) and Numbers ($50,000) are accurate
    r1 = "We have established Project Helios with a budget of $50,000 [Email:101]."
    ok1, err1 = HallucinationFilter.verify_numeric_and_entity_fidelity(db_session, 1, r1, evidence)
    assert ok1
    assert err1 is None

    # 2. FAILURE: Fabricated Number ($75,000)
    r2 = "We have established Project Helios with a budget of $75,000 [Email:101]."
    ok2, err2 = HallucinationFilter.verify_numeric_and_entity_fidelity(db_session, 1, r2, evidence)
    assert not ok2
    assert 'fabricated_number' in err2

    # 3. FAILURE: Fabricated Entity (Project Apollo)
    r3 = "We have established Project Apollo with a budget of $50,000 [Email:101]."
    ok3, err3 = HallucinationFilter.verify_numeric_and_entity_fidelity(db_session, 1, r3, evidence)
    assert not ok3
    assert 'fabricated_entity:Apollo' in err3


def test_verify_timeline_consistency():
    evidence = {
        'thread_evidence': {
            'conv_1': [
                {'citation_payload': {'email_id': 101, 'chunk_id': 'c1', 'source_timestamp': '2024-05-12T10:00:00'}}
            ]
        },
        'attachment_evidence': {}
    }

    # 1. SUCCESS: Year (2024) and Month (May) match email date
    r1 = "John committed to the timeline in May 2024 [Email:101]."
    ok1, err1 = HallucinationFilter.verify_timeline_consistency(r1, evidence)
    assert ok1
    assert err1 is None

    # 2. FAILURE: Fabricated Year (2025)
    r2 = "John committed to the timeline in 2025 [Email:101]."
    ok2, err2 = HallucinationFilter.verify_timeline_consistency(r2, evidence)
    assert not ok2
    assert 'timeline_year_mismatch:2025' in err2

    # 3. FAILURE: Fabricated Month (June)
    r3 = "John committed to the timeline in June 2024 [Email:101]."
    ok3, err3 = HallucinationFilter.verify_timeline_consistency(r3, evidence)
    assert not ok3
    assert 'timeline_month_mismatch:june' in err3


def test_verify_response_gate(db_session):
    # Seed mock chunks in database
    db_session.add(IndexedChunk(
        tenant_id=1, user_id=1, mailbox_id=1, email_id=101,
        chunk_id='c1', chunk_text="John completed the Acme project review.",
        chunk_checksum="sum1", source_start_offset=0, source_end_offset=50,
        token_count=10, vector_id="vec1", content_version=1, semantic_version="2.1"
    ))
    db_session.commit()

    evidence = {
        'thread_evidence': {
            'conv_1': [
                {'citation_payload': {
                    'email_id': 101, 'chunk_id': 'c1', 'source_timestamp': '2024-05-12T10:00:00'
                }}
            ]
        },
        'attachment_evidence': {}
    }

    # 1. Successful grounded verification
    r1 = "John completed the Acme review in May 2024 [Email:101]."
    ok1, res1 = HallucinationFilter.verify_response_gate(db_session, 1, r1, evidence)
    assert ok1
    assert res1 == r1

    # 2. Blocked: Citation Missing/Orphan (returns "Insufficient evidence available.")
    r2 = "John completed the Acme review [Email:102]."
    ok2, res2 = HallucinationFilter.verify_response_gate(db_session, 1, r2, evidence)
    assert not ok2
    assert res2 == "Insufficient evidence available."

    # 3. Blocked: Fabricated Proper Noun (returns "Unable to verify from indexed communications.")
    r3 = "John completed the Beta review in May 2024 [Email:101]."
    ok3, res3 = HallucinationFilter.verify_response_gate(db_session, 1, r3, evidence)
    assert not ok3
    assert res3 == "Unable to verify from indexed communications."
