from collective.opensearch.manager import OpenSearchManager
from plone import api
from plone.restapi.deserializer import json_body
from plone.restapi.services import Service


class OpenSearchService(Service):
    """Base service for OpenSearch management."""

    def __init__(self, context, request):
        super().__init__(context, request)
        self.es = OpenSearchManager()


class Info(OpenSearchService):
    """OpenSearch information."""

    def reply(self):
        info = self.es.info
        response = dict(info)
        response["@id"] = f"{api.portal.get().absolute_url()}/@opensearch"
        return response


class Maintenance(OpenSearchService):
    """OpenSearch integration management."""

    def reply(self):
        data = json_body(self.request)
        action = data.get("action")
        if action == "convert":
            self.es._convert_catalog_to_opensearch()
        elif action == "rebuild":
            catalog = api.portal.get_tool("portal_catalog")
            catalog.manage_catalogRebuild()
        else:
            return self.reply_no_content(status=400)
        return self.reply_no_content()
