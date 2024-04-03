from collective.opensearch.interfaces import IOpenSearchSettings
from collective.opensearch.manager import OpenSearchManager
from collective.opensearch.utils import is_redis_available
from collective.opensearch.engine.exceptions import ConnectionError as conerror
from plone import api
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from urllib3.exceptions import NewConnectionError
from z3c.form import form


class OpenSearchControlPanelForm(RegistryEditForm):
    form.extends(RegistryEditForm)
    schema = IOpenSearchSettings

    label = "OpenSearch Search Settings"

    control_panel_view = "@@opensearch-controlpanel"

    def updateWidgets(self):
        super().updateWidgets()
        if not is_redis_available():
            self.widgets["use_redis"].disabled = "disabled"


class OpenSearchControlPanelFormWrapper(ControlPanelFormWrapper):
    index = ViewPageTemplateFile("controlpanel_layout.pt")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal_catalog = api.portal.get_tool("portal_catalog")
        self.es = OpenSearchManager()

    @property
    def connection_status(self):
        try:
            return self.es.connection.status()["ok"]
        except conerror:
            return False
        except (
            conerror,
            ConnectionError,
            NewConnectionError,
            ConnectionRefusedError,
            AttributeError,
        ):
            try:
                health_status = self.es.connection.cluster.health()["status"]
                return health_status in ("green", "yellow")
            except (
                conerror,
                ConnectionError,
                NewConnectionError,
                ConnectionRefusedError,
                AttributeError,
            ):
                return False

    @property
    def os_info(self):
        return self.os.info

    @property
    def enabled(self):
        return self.os.enabled

    @property
    def active(self):
        return self.os.active

    @property
    def enable_data_sync(self):
        if self.os_info:
            info = dict((key, value) for key, value in self.os_info)
            opensearch_docs = info["Number of docs"]
            catalog_objs = info["Number of docs (Catalog)"]
            if opensearch_docs != catalog_objs:
                return dict(opensearch_docs=opensearch_docs, catalog_objs=catalog_objs)
            return False


OpenSearchControlPanelView = layout.wrap_form(
    OpenSearchControlPanelForm, OpenSearchControlPanelFormWrapper
)
