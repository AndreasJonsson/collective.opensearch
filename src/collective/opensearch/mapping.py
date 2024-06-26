from collective.opensearch.indexes import getIndex
from collective.opensearch.interfaces import IMappingProvider
from zope.interface import implementer


@implementer(IMappingProvider)
class MappingAdapter:
    _default_mapping = {
        "SearchableText": {"store": False, "type": "text", "index": True},
        "Title": {"store": True, "type": "text", "index": True},
        "Description": {"store": True, "type": "text", "index": True},
        "allowedRolesAndUsers": {"store": True, "type": "keyword", "index": True},
        "portal_type": {"store": True, "type": "keyword", "index": True},
    }

    _search_attributes = [
        "Title",
        "Description",
        "Subject",
        "contentType",
        "created",
        "modified",
        "effective",
        "hasImage",
        "is_folderish",
        "portal_type",
        "review_state",
        "path.path",
    ]

    def __init__(self, request, manager):
        self.request = request
        self.manager = manager
        self.catalog = manager.catalog._catalog

    def get_index_creation_body(self):  # NOQA E0211
        return {}

    def __call__(self):
        manager = self.manager
        properties = self._default_mapping.copy()
        for name in self.catalog.indexes.keys():
            index = getIndex(self.catalog, name)
            if index is not None:
                properties[name] = index.create_mapping(name)
            else:
                raise Exception(f"Can not locate index for {name}")

        conn = manager.connection
        index_name = manager.index_name
        if conn.indices.exists(index_name):
            # created BEFORE we started creating this as aliases to versions,
            # we can't go anywhere from here beside try updating...
            pass
        else:
            if not manager.index_version:
                # need to initialize version value
                manager._bump_index_version()
            index_name_v = f"{index_name}_{manager.index_version}"
            if not conn.indices.exists(index_name_v):
                conn.indices.create(index_name_v, body=self.get_index_creation_body())
            if not conn.indices.exists_alias(name=index_name):
                conn.indices.put_alias(index=index_name_v, name=index_name)

        for key in properties:
            if key in self._search_attributes:
                properties[key]["store"] = True

        properties["attachments"] = {
            "properties": {
                "data": {"type": "binary"},
                "filename": {"type": "text"},
                "fieldname": {"type": "text"},
            }
        }

        return {"properties": properties}
