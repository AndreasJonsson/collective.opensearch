from collective.elasticsearch.interfaces import IElasticSettings
from plone.registry.interfaces import IRegistry
from zope.component import getUtility


try:
    from plone.uuid.interfaces import IUUID  # NOQA C0412
except ImportError:

    def IUUID(obj, default=None):  # NOQA W0613
        return default


def getUID(obj):
    value = IUUID(obj, None)
    if not value and hasattr(obj, "UID"):
        value = obj.UID()
    return value


def getESOnlyIndexes():
    try:
        return (
            getUtility(IRegistry)
            .forInterface(IElasticSettings, check=False)
            .es_only_indexes
            or set()
        )
    except (KeyError, AttributeError):
        return {"Title", "Description", "SearchableText"}
