from collective.elasticsearch.interfaces import IElasticSettings
from plone.registry.interfaces import IRegistry
from plone.uuid.interfaces import IUUID
from zope.component import getUtility


def getUID(obj):
    value = IUUID(obj, None)
    if not value and hasattr(obj, "UID"):
        value = obj.UID()
    return value


def get_settings():
    """Return IElasticSettings values."""
    registry = getUtility(IRegistry)
    try:
        settings = registry.forInterface(IElasticSettings, check=False)
    except Exception:  # noQA
        settings = None
    return settings


def getESOnlyIndexes():
    settings = get_settings()
    try:
        return settings.es_only_indexes or set()
    except (KeyError, AttributeError):
        return {"Title", "Description", "SearchableText"}
