from app.services.attachment_parsers import parse_attachment, AttachmentParserError


def test_txt_parser(tmp_path):
    p = tmp_path / 'x.txt'
    p.write_text('hello world')
    out = parse_attachment(str(p), 'text/plain', timeout_seconds=2)
    assert 'hello world' in out


def test_unsupported_parser(tmp_path):
    p = tmp_path / 'x.bin'
    p.write_bytes(b'123')
    try:
        parse_attachment(str(p), 'image/png')
        assert False
    except AttachmentParserError:
        assert True


def test_mime_validation_failure(tmp_path):
    p = tmp_path / 'x.txt'
    p.write_text('hello')
    try:
        parse_attachment(str(p), 'application/pdf')
        assert False
    except AttachmentParserError as e:
        assert 'mime_validation_failed' in str(e)
