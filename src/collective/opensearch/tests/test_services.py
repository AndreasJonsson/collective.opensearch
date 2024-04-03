from collective.opensearch.testing import OpenSearch_API_TESTING
from collective.opensearch.testing import OpenSearch_REDIS_TESTING
from collective.opensearch.tests import BaseAPITest
from parameterized import parameterized_class
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.restapi.testing import RelativeSession


@parameterized_class(
    [{"layer": OpenSearch_API_TESTING}, {"layer": OpenSearch_REDIS_TESTING}]
)
class TestService(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.portal = self.layer["portal"]
        self.portal_url = self.portal.absolute_url()
        self.request = self.portal.REQUEST
        self.api_session = RelativeSession(self.portal_url)
        self.api_session.headers.update({"Accept": "application/json"})
        self.api_session.auth = (SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

    def tearDown(self):
        self.api_session.close()

    def test_get(self):
        response = self.api_session.get("/@opensearch")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")

        results = response.json()
        self.assertEqual(results["@id"], f"{self.portal.absolute_url()}/@opensearch")
        self.assertIn("Cluster Name", results.keys())
        self.assertIn("OpenSearch Version", results.keys())
        self.assertIn("Number of docs (Catalog)", results.keys())
        self.assertIn("Index Name", results.keys())
        self.assertIn("Number of docs", results.keys())
        self.assertIn("Deleted docs", results.keys())
        self.assertIn("Size", results.keys())
        self.assertIn("Query Count", results.keys())

    def test_post_convert(self):
        response = self.api_session.post("/@opensearch", json={"action": "convert"})

        self.assertEqual(response.status_code, 204)

    def test_post_rebuild(self):
        response = self.api_session.post("/@opensearch", json={"action": "rebuild"})

        self.assertEqual(response.status_code, 204)

    def test_post_invalid(self):
        response = self.api_session.post(
            "/@opensearch", json={"action": "bad_action"}
        )

        self.assertEqual(response.status_code, 400)

    def test_control_panel_registered(self):
        response = self.api_session.get("/@controlpanels")
        data = response.json()
        titles = [panel["title"] for panel in data]
        self.assertIn("OpenSearch", titles)

    def test_control_panel_schema(self):
        response = self.api_session.get("/@controlpanels/opensearch")
        data = response.json()
        self.assertEqual(data["title"], "OpenSearch")
        self.assertEqual(data["group"], "Add-on Configuration")
        self.assertTrue(data["data"]["enabled"])
        self.assertTrue("enabled", data["schema"]["fieldsets"][0]["fields"])
