from .fetch import fetch_blob_data
from .fetch import fetch_data
from collective.opensearch import local
from collective.opensearch.manager import OpenSearchManager
from opensearchpy import OpenSearch
from rq import Queue
from rq import Retry
from rq.decorators import job

import cbor2
import os
import redis


REDIS_CONNECTION_KEY = "redis_connection"


def redis_connection():
    connection = local.get_local(REDIS_CONNECTION_KEY)
    if not connection:
        local.set_local(
            REDIS_CONNECTION_KEY,
            redis.Redis.from_url(os.environ.get("PLONE_REDIS_DSN", None)),
        )
        connection = local.get_local(REDIS_CONNECTION_KEY)
    return connection


def os_connection(hosts, **params):
    connection = local.get_local(OpenSearchManager.connection_key)
    if not connection:
        local.set_local(
            OpenSearchManager.connection_key, OpenSearch(hosts, **params)
        )
        connection = local.get_local(OpenSearchManager.connection_key)
    return connection


queue = Queue(
    "normal",
    connection=redis_connection(),
    is_async=os.environ.get("ZOPETESTCASE", "0") == "0",
)  # Don't queue in tests

queue_low = Queue(
    "low",
    connection=redis_connection(),
    is_async=os.environ.get("ZOPETESTCASE", "0") == "0",
)  # Don't queue in tests


@job(queue, retry=Retry(max=3, interval=30))
def bulk_update(hosts, params, index_name, body):
    """
    Collects all the data and updates opensearch
    """
    hosts = os.environ.get("PLONE_OPENSEARCH_HOST", hosts)
    connection = os_connection(hosts, **params)

    for item in body:
        if len(item) == 1 and "delete" in item[0]:
            continue

        catalog_info, payload = item
        action, index_info = list(catalog_info.items())[0]
        if action == "index":
            data = fetch_data(uuid=index_info["_id"], attributes=list(payload.keys()))
            item[1] = data
        elif action == "update":
            data = fetch_data(
                uuid=index_info["_id"], attributes=list(payload["doc"].keys())
            )
            item[1]["doc"] = data

    os_data = [item for sublist in body for item in sublist]
    connection.bulk(index=index_name, body=os_data)
    return "Done"


@job(queue_low)
def update_file_data(hosts, params, index_name, body):
    """
    Get blob data from plone and index it via opensearch attachment pipeline
    """
    hosts = os.environ.get("PLONE_OPENSEARCH_HOST", hosts)
    connection = os_connection(hosts, **params)
    uuid, data = body

    attachments = {"attachments": []}

    for fieldname, content in data.items():
        file_ = fetch_blob_data(fieldname, data)
        attachments["attachments"].append(
            {
                "filename": content["filename"],
                "fieldname": fieldname,
                "data": file_.read(),
            }
        )

    connection.update(
        index_name,
        uuid,
        cbor2.dumps({"doc": attachments}),
        headers={"content-type": "application/cbor"},
    )
    return "Done"
