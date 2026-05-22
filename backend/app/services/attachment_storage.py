from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class AttachmentStorageError(Exception):
    pass


_SAFE = re.compile(r'[^a-zA-Z0-9._-]+')


@dataclass
class StoredAttachment:
    path: str
    checksum: str
    size_bytes: int


class AttachmentStorageProvider(Protocol):
    def save(self, tenant_id: int, attachment_id: int, filename: str, content: bytes) -> StoredAttachment: ...
    def resolve(self, tenant_id: int, relative_path: str) -> str: ...


class LocalAttachmentStorage:
    def __init__(self, base_path: str, max_size_bytes: int = 25 * 1024 * 1024):
        self.base = Path(base_path)
        self.max_size_bytes = max_size_bytes
        self.base.mkdir(parents=True, exist_ok=True)

    def _sanitize(self, filename: str) -> str:
        cleaned = _SAFE.sub('_', filename).strip('._')
        return cleaned or 'attachment.bin'

    def save(self, tenant_id: int, attachment_id: int, filename: str, content: bytes) -> StoredAttachment:
        if len(content) > self.max_size_bytes:
            raise AttachmentStorageError('attachment_too_large')
        checksum = hashlib.sha256(content).hexdigest()
        safe_name = self._sanitize(filename)
        tenant_dir = self.base / f'tenant_{tenant_id}'
        tenant_dir.mkdir(parents=True, exist_ok=True)
        path = tenant_dir / f'{attachment_id}_{safe_name}'
        path.write_bytes(content)
        return StoredAttachment(path=str(path), checksum=checksum, size_bytes=len(content))

    def resolve(self, tenant_id: int, relative_path: str) -> str:
        candidate = (self.base / relative_path).resolve()
        tenant_root = (self.base / f'tenant_{tenant_id}').resolve()
        if not str(candidate).startswith(str(tenant_root)):
            raise AttachmentStorageError('path_traversal_blocked')
        if not candidate.exists():
            raise AttachmentStorageError('attachment_missing')
        return str(candidate)
