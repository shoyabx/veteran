from __future__ import annotations
import asyncio
import logging
from typing import Optional, Any
import httpx

logger = logging.getLogger('graph')

class GraphAPIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, retryable: bool = False):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(f'{status_code} {code}: {message}')

class MicrosoftGraphClient:
    BASE_URL = 'https://graph.microsoft.com/v1.0'

    def __init__(self, access_token: str, timeout: float = 20.0):
        self.access_token = access_token
        self.timeout = timeout

    async def _request(self, method: str, url: str, params: Optional[dict[str, Any]] = None) -> dict:
        headers = {'Authorization': f'Bearer {self.access_token}', 'Accept': 'application/json'}
        retries = 3
        backoff = 1.0
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, retries + 1):
                response = await client.request(method, url, headers=headers, params=params)
                if response.status_code in (429, 503):
                    if attempt == retries:
                        break
                    retry_after = response.headers.get('Retry-After')
                    sleep_for = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                    await asyncio.sleep(sleep_for)
                    backoff *= 2
                    continue
                if response.status_code >= 400:
                    payload = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error = payload.get('error', {})
                    raise GraphAPIError(response.status_code, error.get('code', 'graph_error'), error.get('message', 'Graph request failed'), retryable=response.status_code >= 500)
                return response.json()
        raise GraphAPIError(429, 'throttled', 'Graph throttling persisted after retries', retryable=True)

    async def list_inbox_messages_page(self, top: int = 50, next_link: Optional[str] = None) -> dict:
        if next_link:
            return await self._request('GET', next_link)
        params = {
            '$top': top,
            '$select': 'id,internetMessageId,conversationId,subject,sender,toRecipients,ccRecipients,bccRecipients,sentDateTime,receivedDateTime,body,importance,categories,hasAttachments,inReplyTo,conversationIndex',
            '$orderby': 'receivedDateTime desc',
        }
        return await self._request('GET', f'{self.BASE_URL}/me/mailFolders/inbox/messages', params=params)

    async def delta_messages_page(self, delta_link: Optional[str] = None, top: int = 50) -> dict:
        if delta_link:
            return await self._request('GET', delta_link)
        params = {
            '$top': top,
            '$select': 'id,internetMessageId,conversationId,subject,sender,toRecipients,ccRecipients,bccRecipients,sentDateTime,receivedDateTime,body,importance,categories,hasAttachments,inReplyTo,parentFolderId,lastModifiedDateTime',
        }
        return await self._request('GET', f'{self.BASE_URL}/me/mailFolders/inbox/messages/delta', params=params)

    async def list_attachments(self, message_id: str, top: int = 50, next_link: Optional[str] = None) -> dict:
        if next_link:
            return await self._request('GET', next_link)
        params = {'$top': top, '$select': 'id,name,contentType,size,isInline,lastModifiedDateTime'}
        return await self._request('GET', f'{self.BASE_URL}/me/messages/{message_id}/attachments', params=params)
