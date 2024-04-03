from collective.opensearch import utils
from collective.opensearch.browser.controlpanel import OpenSearchControlPanelView
from collective.opensearch.interfaces import IOpenSearchIndexQueueProcessor
from collective.opensearch.manager import OpenSearchManager
from collective.opensearch.testing import OpenSearch_API_TESTING
from collective.opensearch.testing import OpenSearch_FUNCTIONAL_TESTING
from collective.opensearch.testing import OpenSearch_INTEGRATION_TESTING
from collective.opensearch.testing import OpenSearch_REDIS_TESTING
from plone import api
from Products.CMFCore.indexing import processQueue
from zope.component import getUtility

import os
import time
import transaction
import unittest


MAX_CONNECTION_RETRIES = 20


class BaseTest(unittest.TestCase):
    layer = OpenSearch_INTEGRATION_TESTING

    def get_processor(self):
        return getUtility(IOpenSearchIndexQueueProcessor, name="opensearch")

    def setUp(self):
        super().setUp()
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]
        self.request.environ["testing"] = True
        self.app = self.layer["app"]

        os.environ["PLONE_BACKEND"] = self.portal.absolute_url()

        settings = utils.get_settings()
        # disable sniffing hosts in tests because docker...
        settings.sniffer_timeout = None
        settings.enabled = True
        settings.sniffer_timeout = 0.0

        # Raise opensearch exceptions
        settings.raise_search_exception = True

        self._wait_for_os_service()

        self.catalog = api.portal.get_tool("portal_catalog")
        self.catalog._opensearchcustomindex = "plone-test-index"
        self.os = OpenSearchManager()

        self.catalog.manage_catalogRebuild()
        # need to commit here so all tests start with a baseline
        # of opensearch enabled
        time.sleep(0.1)
        self.commit()

    def commit(self, wait: int = 0):
        processQueue()
        transaction.commit()
        self.os.flush_indices()
        if wait:
            time.sleep(wait)

    def tearDown(self):
        super().tearDown()
        real_index_name = f"{self.os.real_index_name}_1"
        index_name = self.os.index_name
        conn = self.os.connection
        conn.indices.delete_alias(index=real_index_name, name=index_name)
        conn.indices.delete(index=real_index_name)
        conn.indices.flush()
        # Wait ES remove the index
        time.sleep(0.1)

    def _wait_for_os_service(self):
        controlpanel = OpenSearchControlPanelView(self.portal, self.request)
        counter = 0
        while not controlpanel.connection_status:
            if counter == MAX_CONNECTION_RETRIES:
                raise Exception("Cannot connect to opensearch service")
            time.sleep(1)
            counter += 1


class BaseFunctionalTest(BaseTest):
    layer = OpenSearch_FUNCTIONAL_TESTING

    def search(self, query: dict):
        return self.catalog(**query)

    def total_results(self, query: dict):
        results = self.search(query)
        return len(results)


class BaseAPITest(BaseTest):

    layer = OpenSearch_API_TESTING


class BaseRedisTest(BaseTest):

    layer = OpenSearch_REDIS_TESTING
