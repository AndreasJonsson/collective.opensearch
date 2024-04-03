from collective.opensearch import utils
from plone import api
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing import zope

import collective.opensearch
import os
import redis
import time


MAX_CONNECTION_RETRIES = 20


class OpenSearch(PloneSandboxLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        super().setUpZope(app, configurationContext)
        self.loadZCML(package=collective.opensearch)

    def setUpPloneSite(self, portal):
        super().setUpPloneSite(portal)
        # install into the Plone site
        applyProfile(portal, "collective.opensearch:default")
        setRoles(portal, TEST_USER_ID, ("Member", "Manager"))
        workflowTool = api.portal.get_tool("portal_workflow")
        workflowTool.setDefaultChain("plone_workflow")


OpenSearch_FIXTURE = OpenSearch()
OpenSearch_INTEGRATION_TESTING = IntegrationTesting(
    bases=(OpenSearch_FIXTURE,), name="OpenSearch:Integration"
)
OpenSearch_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(OpenSearch_FIXTURE,), name="OpenSearch:Functional"
)
OpenSearch_API_TESTING = FunctionalTesting(
    bases=(OpenSearch_FIXTURE, zope.WSGI_SERVER_FIXTURE),
    name="OpenSearch:API",
)


class RedisOpenSearch(OpenSearch):
    def setUpPloneSite(self, portal):
        super().setUpPloneSite(portal)

        # Setup environ for redis testing
        os.environ["PLONE_BACKEND"] = portal.absolute_url()
        os.environ["PLONE_USERNAME"] = SITE_OWNER_NAME
        os.environ["PLONE_PASSWORD"] = SITE_OWNER_PASSWORD
        os.environ["PLONE_REDIS_DSN"] = "redis://localhost:6379/0"

        # Make sure tasks are not handled async in tests
        # from collective.opensearch.redis.tasks import queue
        # queue._is_async = False

        utils.get_settings().use_redis = True
        self._wait_for_redis_service()

    def _wait_for_redis_service(self):
        from collective.opensearch.redis.tasks import redis_connection

        counter = 0
        while True:
            if counter == MAX_CONNECTION_RETRIES:
                raise Exception("Cannot connect to redis service")
            try:
                if redis_connection().ping():
                    break
            except redis.ConnectionError:
                time.sleep(1)
                counter += 1


OpenSearch_REDIS_FIXTURE = RedisOpenSearch()
OpenSearch_REDIS_TESTING = FunctionalTesting(
    bases=(zope.WSGI_SERVER_FIXTURE, OpenSearch_REDIS_FIXTURE),
    name="OpenSearch:Redis",
)
