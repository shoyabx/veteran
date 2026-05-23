import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.indexing import IndexedChunk, AttachmentChunk
from app.services.synthesis_service import SynthesisService

@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    IndexedChunk.__table__.create(bind=engine)
    AttachmentChunk.__table__.create(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def make_mock_completion(text: str):
    completion = MagicMock()
    choice = MagicMock()
    message = MagicMock()
    message.content = text
    choice.message = message
    completion.choices = [choice]
    return completion

def test_synthesis_empty_evidence(db_session):
    # If no evidence is provided, it should immediately return "No matching email found."
    ans, metrics = SynthesisService.synthesize(db_session, 1, "Helios budget", {}, "corr-1")
    assert ans == "No matching email found."
    assert metrics['synthesis_validation_status'] == 'no_evidence'

def test_synthesis_successful_grounding(db_session):
    # Seed mock chunk in SQLite
    db_session.add(IndexedChunk(
        tenant_id=1, user_id=1, mailbox_id=1, email_id=101,
        chunk_id='c1', chunk_text="John approved the Project Helios budget of $50,000.",
        chunk_checksum="sum1", source_start_offset=0, source_end_offset=50,
        token_count=10, vector_id="vec1", content_version=1, semantic_version="2.1"
    ))
    db_session.commit()

    evidence = {
        'thread_evidence': {
            'conv_1': [
                {
                    'chunk_id': 'c1',
                    'citation_payload': {
                        'email_id': 101,
                        'chunk_id': 'c1', # Crucial fix
                        'sender': 'alice@test.com',
                        'recipient': 'bob@test.com',
                        'subject': 'Project Helios',
                        'source_timestamp': '2026-05-12T10:00:00'
                    }
                }
            ]
        },
        'attachment_evidence': {},
        'evidence_count': 1
    }

    mock_llm_response = "John approved the Project Helios budget of $50,000 [Email:101]."

    with patch('openai.resources.chat.completions.Completions.create') as mock_create:
        mock_create.return_value = make_mock_completion(mock_llm_response)

        ans, metrics = SynthesisService.synthesize(db_session, 1, "Helios budget", evidence, "corr-2")
        
        assert ans == mock_llm_response
        assert metrics['synthesis_validation_status'] == 'validated'
        assert metrics['unsupported_claim_risk'] == 0.0
        assert metrics['retrieval_coverage_score'] == 1.0
        assert metrics['evidence_snapshot_hash'] is not None

def test_synthesis_regeneration_retry_loop(db_session):
    db_session.add(IndexedChunk(
        tenant_id=1, user_id=1, mailbox_id=1, email_id=101,
        chunk_id='c1', chunk_text="John approved the Project Helios budget of $50,000.",
        chunk_checksum="sum1", source_start_offset=0, source_end_offset=50,
        token_count=10, vector_id="vec1", content_version=1, semantic_version="2.1"
    ))
    db_session.commit()

    evidence = {
        'thread_evidence': {
            'conv_1': [
                {
                    'chunk_id': 'c1',
                    'citation_payload': {
                        'email_id': 101,
                        'chunk_id': 'c1', # Crucial fix
                        'sender': 'alice@test.com',
                        'recipient': 'bob@test.com',
                        'subject': 'Project Helios',
                        'source_timestamp': '2026-05-12T10:00:00'
                    }
                }
            ]
        },
        'attachment_evidence': {},
        'evidence_count': 1
    }

    # First attempt: Fabricated company Apollo and number $75,000
    r1 = "John approved the Apollo budget of $75,000 [Email:101]."
    # Second attempt: Corrected facts
    r2 = "John approved the Project Helios budget of $50,000 [Email:101]."

    with patch('openai.resources.chat.completions.Completions.create') as mock_create:
        mock_create.side_effect = [
            make_mock_completion(r1),
            make_mock_completion(r2)
        ]

        ans, metrics = SynthesisService.synthesize(db_session, 1, "Helios budget", evidence, "corr-3")
        
        assert ans == r2
        assert metrics['synthesis_validation_status'] == 'regenerated'
        assert metrics['unsupported_claim_risk'] == 0.0

def test_synthesis_exhaustive_failure_fallback(db_session):
    db_session.add(IndexedChunk(
        tenant_id=1, user_id=1, mailbox_id=1, email_id=101,
        chunk_id='c1', chunk_text="John approved the Project Helios budget of $50,000.",
        chunk_checksum="sum1", source_start_offset=0, source_end_offset=50,
        token_count=10, vector_id="vec1", content_version=1, semantic_version="2.1"
    ))
    db_session.commit()

    evidence = {
        'thread_evidence': {
            'conv_1': [
                {
                    'chunk_id': 'c1',
                    'citation_payload': {
                        'email_id': 101,
                        'chunk_id': 'c1', # Crucial fix
                        'sender': 'alice@test.com',
                        'recipient': 'bob@test.com',
                        'subject': 'Project Helios',
                        'source_timestamp': '2026-05-12T10:00:00'
                    }
                }
            ]
        },
        'attachment_evidence': {},
        'evidence_count': 1
    }

    # Stubbornly returns ungrounded numbers ($75,000) every time
    r1 = "John approved the Project Helios budget of $75,000 [Email:101]."

    with patch('openai.resources.chat.completions.Completions.create') as mock_create:
        mock_create.side_effect = [
            make_mock_completion(r1),
            make_mock_completion(r1),
            make_mock_completion(r1)
        ]

        ans, metrics = SynthesisService.synthesize(db_session, 1, "Helios budget", evidence, "corr-4")
        
        assert ans == "Unable to verify from indexed communications."
        assert metrics['synthesis_validation_status'] == 'blocked_fallback'
        assert metrics['unsupported_claim_risk'] == 1.0
