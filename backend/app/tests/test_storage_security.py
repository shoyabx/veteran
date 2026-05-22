from app.services.attachment_storage import LocalAttachmentStorage, AttachmentStorageError


def test_tenant_storage_isolation(tmp_path):
    s = LocalAttachmentStorage(str(tmp_path))
    stored = s.save(tenant_id=1, attachment_id=10, filename='doc.txt', content=b'abc')
    rel = stored.path.split(str(tmp_path) + '/')[1]
    assert s.resolve(1, rel).endswith('doc.txt')


def test_path_traversal_blocked(tmp_path):
    s = LocalAttachmentStorage(str(tmp_path))
    try:
        s.resolve(1, '../etc/passwd')
        assert False
    except AttachmentStorageError as e:
        assert 'path_traversal_blocked' in str(e)
