import pytest
from app.services.graph_client import MicrosoftGraphClient, GraphAPIError


@pytest.mark.asyncio
async def test_delta_uses_next_link_when_provided(monkeypatch):
    client = MicrosoftGraphClient('token')
    called = {}

    async def fake_request(method, url, params=None):
        called['url'] = url
        called['params'] = params
        return {'value': []}

    client._request = fake_request
    await client.delta_messages_page(delta_link='https://graph.microsoft.com/v1.0/next')
    assert called['url'] == 'https://graph.microsoft.com/v1.0/next'
    assert called['params'] is None


@pytest.mark.asyncio
async def test_inbox_page_builds_correct_endpoint(monkeypatch):
    client = MicrosoftGraphClient('token')
    called = {}

    async def fake_request(method, url, params=None):
        called['url'] = url
        called['params'] = params
        return {'value': []}

    client._request = fake_request
    await client.list_inbox_messages_page(top=25)
    assert called['url'].endswith('/me/mailFolders/inbox/messages')
    assert called['params']['$top'] == 25
