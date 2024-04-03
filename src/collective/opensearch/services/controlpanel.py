from collective.opensearch.interfaces import IOpenSearchLayer
from collective.opensearch.interfaces import IOpenSearchSettings
from plone.restapi.controlpanels import RegistryConfigletPanel
from zope.component import adapter
from zope.interface import Interface


@adapter(Interface, IOpenSearchLayer)
class OpenSearchSettingsConfigletPanel(RegistryConfigletPanel):
    """Control Panel endpoint"""

    schema = IOpenSearchSettings
    configlet_id = "opensearch"
    configlet_category_id = "Products"
    title = "OpenSearch Settings"
    group = ""
    schema_prefix = "collective.opensearch.interfaces.IOpenSearchSettings"
