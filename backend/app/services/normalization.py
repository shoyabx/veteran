from __future__ import annotations
from datetime import datetime, timezone
import re
from html import unescape

TAG_RE = re.compile(r'<[^>]+>')


def _parse_iso(value: str | None):
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)


def html_to_text(html: str | None) -> str | None:
    if not html:
        return None
    text = TAG_RE.sub(' ', html)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_message(msg: dict) -> dict:
    body = msg.get('body') or {}
    body_html = body.get('content') if body.get('contentType', '').lower() == 'html' else None
    body_text = html_to_text(body_html) if body_html else body.get('content')

    sender = (msg.get('sender') or {}).get('emailAddress') or {}

    headers = msg.get('internetMessageHeaders') or []
    references_value = '; '.join([f"{h.get('name')}={h.get('value')}" for h in headers if isinstance(h, dict)]) if headers else None

    return {
        'graph_message_id': msg.get('id'),
        'internet_message_id': msg.get('internetMessageId'),
        'conversation_id': msg.get('conversationId'),
        'subject': msg.get('subject'),
        'sender_email': sender.get('address'),
        'sender_name': sender.get('name'),
        'sent_at': _parse_iso(msg.get('sentDateTime')),
        'received_at': _parse_iso(msg.get('receivedDateTime')),
        'body_text': body_text,
        'body_html': body_html,
        'importance': msg.get('importance'),
        'categories': msg.get('categories') or [],
        'has_attachments': bool(msg.get('hasAttachments')),
        'in_reply_to': msg.get('inReplyTo'),
        'references_header': references_value,
        'parent_message_id': None,
        'is_deleted': bool('@removed' in msg),
        'raw_etag': msg.get('@odata.etag'),
    }


def normalize_participants(msg: dict) -> list[dict]:
    out = []
    for role, key in [('to', 'toRecipients'), ('cc', 'ccRecipients'), ('bcc', 'bccRecipients')]:
        for item in msg.get(key) or []:
            ea = item.get('emailAddress') or {}
            if ea.get('address'):
                out.append({'role': role, 'email': ea.get('address'), 'name': ea.get('name')})
    return out
