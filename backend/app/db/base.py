from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"
