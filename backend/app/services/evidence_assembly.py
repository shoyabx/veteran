from __future__ import annotations

from collections import defaultdict


def assemble_evidence(rows: list[dict]) -> dict:
    threads: dict[str, list[dict]] = defaultdict(list)
    attachments: dict[str, list[dict]] = defaultdict(list)

    for r in rows:
        p = r['citation_payload']
        conv = str(p.get('conversation_id') or 'none')
        att = str(p.get('attachment_id') or 'none')
        threads[conv].append(r)
        attachments[att].append(r)

    for conv in threads:
        threads[conv].sort(key=lambda x: (x['citation_payload'].get('source_timestamp') or '', x['rank']))

    return {
        'thread_evidence': dict(threads),
        'attachment_evidence': dict(attachments),
        'evidence_count': len(rows),
    }
