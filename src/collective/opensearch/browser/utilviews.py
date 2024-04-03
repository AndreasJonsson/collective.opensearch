from AccessControl import Unauthorized
from Acquisition import aq_parent
from collective.opensearch.manager import OpenSearchManager
from opensearchpy.exceptions import NotFoundError
from opensearchpy.helpers import scan
from plone import api
from Products.CMFCore.indexing import processQueue
from Products.Five.browser import BrowserView
from zope.component import getMultiAdapter

import logging
import time
import transaction


logger = logging.getLogger(__name__)


class Utils(BrowserView):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._count_index_object = 0
        self._count_del_doc_opensearch = 0

    def convert(self):
        if self.request.method == "POST":
            authenticator = getMultiAdapter(
                (self.context, self.request), name="authenticator"
            )
            if not authenticator.verify():
                raise Unauthorized

            self._os._convert_catalog_to_opensearch()
        site = aq_parent(self.context)
        self.request.response.redirect(f"{site.absolute_url()}/@@opensearch-controlpanel")

    def rebuild(self):
        if self.request.method == "POST":
            authenticator = getMultiAdapter(
                (self.context, self.request), name="authenticator"
            )
            if not authenticator.verify():
                raise Unauthorized

            self.context.manage_catalogRebuild()

        site = aq_parent(self.context)
        self.request.response.redirect(f"{site.absolute_url()}/@@opensearch-controlpanel")

    def synchronize(self):
        if self.request.method == "POST":
            authenticator = getMultiAdapter(
                (self.context, self.request), name="authenticator"
            )
            if not authenticator.verify():
                raise Unauthorized
            uids_catalog = set(self._uids_catalog)
            uids_opensearch = set(self._uids_opensearch)
            uids_not_in_opensearch = uids_catalog.difference(uids_opensearch)
            logger.info(
                (
                    f"{len(uids_not_in_opensearch)} "
                    f"non-indexed objects in opensearch"
                )
            )
            uids_not_in_catalog = uids_opensearch.difference(uids_catalog)
            logger.info(
                (f"{len(uids_not_in_catalog)} documents " f"not found in the catalog.")
            )
            self._index_object_in_opensearch(uids_not_in_opensearch)
            self._delete_document_opensearch(uids_not_in_catalog)
            message = (
                f"Indexed objects: {self._count_index_object} "
                f"Documents deleted: {self._count_del_doc_opensearch}"
            )
            logger.info(message)
        site = aq_parent(self.context)
        self.request.response.redirect(f"{site.absolute_url()}/@@opensearch-controlpanel")

    @property
    def _os(self):
        return OpenSearchManager()

    @property
    def _os_conn(self):
        return self._os.connection

    @property
    def _uids_catalog(self):
        logger.info("Fetching all uids indexed in the catalog...")
        uids = self.context.portal_catalog.uniqueValuesFor("UID")
        logger.info(f"Found {len(uids)} uids")
        return uids

    @property
    def _uids_opensearch(self):
        query = {"query": {"match_all": {}}, "_source": ["UID"]}
        items = scan(
            self._os_conn,
            index=self._os.index_name,
            query=query,
            preserve_order=True,
            size=10000,
        )
        logger.info("Fetching all indexed uids in opensearch...")
        uids = [item["_id"] for item in items]
        logger.info(f"Found {len(uids)} uids")
        return uids

    def _index_object_in_opensearch(self, uids):
        amount = len(uids)
        for index, uid in enumerate(uids):
            obj = api.content.get(UID=uid)
            obj.indexObject()
            self._count_index_object += 1
            logging.info("indexObject: %s", "/".join(obj.getPhysicalPath()))
            if index % self._os.bulk_size == 0:
                # Force indexing in ES
                self.commit(wait=1)
                logger.info("COMMIT: %s/%s", index, amount - 1)
        self.commit(wait=1)

    def _delete_document_opensearch(self, uids):
        conn = self._os_conn
        amount = len(uids)
        for index, uid in enumerate(uids):
            try:
                conn.delete(index=self._os.index_name, id=uid)
                self._count_del_doc_opensearch += 1
                logging.info("delete doc: %s", uid)
            except NotFoundError:
                continue
            if index % self._os.bulk_size == 0:
                # Force indexing in ES
                self.commit(wait=1)
                logger.info("COMMIT: %s/%s", index, amount - 1)
        self.commit(wait=1)

    def commit(self, wait: int = 0):
        processQueue()
        transaction.commit()
        self._os.flush_indices()
        if wait:
            time.sleep(wait)
