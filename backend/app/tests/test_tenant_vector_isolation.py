from app.services.qdrant_client import TenantQdrant


def test_collection_name_tenant_isolated():
    assert TenantQdrant.collection_name(1) != TenantQdrant.collection_name(2)
    assert TenantQdrant.collection_name(1) == 'tenant_1_emails'
