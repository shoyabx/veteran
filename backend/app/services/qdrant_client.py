from __future__ import annotations
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

class TenantQdrant:
    def __init__(self, url: str, api_key: str | None = None):
        self.client = QdrantClient(url=url, api_key=api_key)

    @staticmethod
    def collection_name(tenant_id: int) -> str:
        return f'tenant_{tenant_id}_emails'

    def ensure_collection(self, tenant_id: int, vector_size: int, distance: str = 'Cosine') -> str:
        name = self.collection_name(tenant_id)
        if not self.client.collection_exists(name):
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=vector_size, distance=getattr(models.Distance, distance.upper())),
            )
            self.client.create_payload_index(name, field_name='tenant_id', field_schema=models.PayloadSchemaType.INTEGER)
            self.client.create_payload_index(name, field_name='email_id', field_schema=models.PayloadSchemaType.INTEGER)
            self.client.create_payload_index(name, field_name='conversation_id', field_schema=models.PayloadSchemaType.KEYWORD)
        return name

    def upsert_vectors(self, tenant_id: int, points: list[models.PointStruct]) -> None:
        self.client.upsert(collection_name=self.collection_name(tenant_id), points=points, wait=True)

    def delete_vectors_by_email(self, tenant_id: int, email_id: int) -> None:
        filt = models.Filter(must=[models.FieldCondition(key='email_id', match=models.MatchValue(value=email_id))])
        self.client.delete(collection_name=self.collection_name(tenant_id), points_selector=models.FilterSelector(filter=filt), wait=True)

    def search_vectors(self, tenant_id: int, query_vector: list[float], top_k: int, score_threshold: float = 0.0, filters: dict | None = None):
        must = [FieldCondition(key='tenant_id', match=MatchValue(value=tenant_id))]
        for f in (filters or {}).get('must', []):
            if 'is_null' in f:
                empty_key = f['is_null'].get('key')
                if empty_key:
                    must.append(models.IsEmptyCondition(key=empty_key))
            else:
                key = f.get('key')
                mv = f.get('match', {}).get('value') if f.get('match') else None
                if key is not None and mv is not None:
                    must.append(FieldCondition(key=key, match=MatchValue(value=mv)))
        filt = Filter(must=must)
        return self.client.search(
            collection_name=self.collection_name(tenant_id),
            query_vector=query_vector,
            query_filter=filt,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )
