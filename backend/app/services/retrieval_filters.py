from __future__ import annotations

from datetime import datetime

ALLOWED_FILTERS = {
    'mailbox_id', 'email_id', 'conversation_id', 'attachment_id',
    'date_from', 'date_to', 'sender', 'recipients', 'categories',
    'has_attachment', 'mode'
}


def validate_filters(filters: dict | None) -> dict:
    filters = filters or {}
    extra = set(filters.keys()) - ALLOWED_FILTERS
    if extra:
        raise ValueError(f'unsupported_filter_keys:{sorted(extra)}')

    if 'mode' in filters and filters['mode'] not in ('email', 'attachment', 'mixed'):
        raise ValueError('invalid_mode_filter')

    if 'date_from' in filters:
        datetime.fromisoformat(filters['date_from'])
    if 'date_to' in filters:
        datetime.fromisoformat(filters['date_to'])

    if 'date_from' in filters and 'date_to' in filters and filters['date_from'] > filters['date_to']:
        raise ValueError('invalid_date_range')

    return filters


def build_qdrant_filter(tenant_id: int, filters: dict) -> dict:
    must = [{'key': 'tenant_id', 'match': {'value': tenant_id}}]
    int_keys = ['mailbox_id', 'email_id', 'attachment_id']
    str_keys = ['conversation_id']
    for k in int_keys:
        if k in filters:
            must.append({'key': k, 'match': {'value': int(filters[k])}})
    for k in str_keys:
        if k in filters:
            must.append({'key': k, 'match': {'value': str(filters[k])}})

    if filters.get('mode') == 'email':
        must.append({'is_null': {'key': 'attachment_id'}})

    return {'must': must}
