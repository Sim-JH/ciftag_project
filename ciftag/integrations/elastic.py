from elasticsearch import Elasticsearch

import ciftag.utils.logger as logger
from ciftag.settings import env_key

logs = logger.Logger(log_dir='Elastic')


class ESManager:
    def __init__(self):
        host = env_key.ES_HOST
        port = env_key.ES_PORT
        scheme = env_key.ES_SCHEME

        # es connection
        self.es = Elasticsearch([{'host': host, 'port': port, 'scheme': scheme}])

    def index_to_es(self, index_name, idx, body):
        """인덱싱"""
        self.es.index(
            index=index_name,
            id=idx,
            body=body
        )

    def search_es_index(self, index_name, body):
        """검색 후 id, source 반환"""
        result = self.es.search(index=index_name, body=body)
        hits = result['hits']['hits']

        # id와 _source를 병합하여 반환
        return [{**{"id": hit["_id"]}, **hit["_source"]} for hit in hits]