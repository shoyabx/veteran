import hashlib
from typing import Tuple

SUPPORTED_MIME = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
}
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024

def validate_attachment(content_type: str, size: int) -> Tuple[bool, str]:
    if size > MAX_ATTACHMENT_BYTES:
        return False, 'attachment_too_large'
    if content_type not in SUPPORTED_MIME:
        return False, 'unsupported_mime'
    return True, 'ok'

def compute_sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()
