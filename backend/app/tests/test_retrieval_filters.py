import pytest
from app.services.retrieval_filters import validate_filters, build_qdrant_filter


def test_filter_validation_blocks_unknown_keys():
    with pytest.raises(ValueError):
        validate_filters({'foo': 'bar'})


def test_filter_validation_mode():
    with pytest.raises(ValueError):
        validate_filters({'mode': 'bad'})


def test_build_filter_includes_tenant():
    f = build_qdrant_filter(tenant_id=9, filters={'mailbox_id': 5})
    keys = [m['key'] for m in f['must'] if 'key' in m]
    assert 'tenant_id' in keys
    assert 'mailbox_id' in keys
