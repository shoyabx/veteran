import pytest
from app.services.normalization import normalize_message, normalize_participants
from app.services.attachment_validator import validate_attachment


def test_normalize_message_basic():
    msg = {
        'id': 'm1',
        'internetMessageId': '<abc@example.com>',
        'conversationId': 'c1',
        'subject': 'Hello',
        'sender': {'emailAddress': {'address': 'a@example.com', 'name': 'A'}},
        'toRecipients': [{'emailAddress': {'address': 'b@example.com', 'name': 'B'}}],
        'sentDateTime': '2024-01-01T00:00:00Z',
        'receivedDateTime': '2024-01-01T00:01:00Z',
        'body': {'contentType': 'HTML', 'content': '<p>hello</p>'},
        'importance': 'normal',
        'categories': ['X'],
        'hasAttachments': True,
    }
    out = normalize_message(msg)
    assert out['graph_message_id'] == 'm1'
    assert out['body_text'] == 'hello'


def test_participants():
    msg = {'toRecipients': [{'emailAddress': {'address': 'b@example.com'}}], 'ccRecipients': [], 'bccRecipients': []}
    out = normalize_participants(msg)
    assert len(out) == 1
    assert out[0]['role'] == 'to'


def test_attachment_validation():
    ok, reason = validate_attachment('application/pdf', 1024)
    assert ok and reason == 'ok'
    ok2, reason2 = validate_attachment('image/png', 1024)
    assert not ok2 and reason2 == 'unsupported_mime'
