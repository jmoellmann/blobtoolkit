#!/usr/bin/env python3
"""Dataset Class module."""

# pylint: disable=no-member, too-many-nested-blocks, too-many-branches, too-many-instance-attributes


class Metadata():
    """Class for field and dataset metadata."""

    __slots__ = ['dataset_id',
                 'assembly',
                 '_field_ids',
                 '_field_list',
                 'fields',
                 'links',
                 'name',
                 'origin',
                 'parents',
                 'plot',
                 'reads',
                 'record_type',
                 'records',
                 'settings',
                 'similarity',
                 'static_fields',
                 'taxon'
                 ]

    def __init__(self, dataset_id, **kwargs):
        """Init Dataset class."""
        self.dataset_id = dataset_id
        self.fields = []
        self.name = dataset_id
        self.links = {}
        self.assembly = {}
        self.plot = {}
        self.record_type = 'record'
        self.records = 0
        self.update_data(**kwargs)
        self._field_list = self.list_fields()
        self._field_ids = list(self._field_list.keys())

    def update_data(self, **kwargs):
        """Update values and keys for an existing field."""
        for key, value in kwargs.items():
            if key == 'id':
                key = 'dataset_id'
            setattr(self, key, value)

    def list_fields(self):
        """List all fields in dataset."""
        field_ids = self._list_fields(self.fields)
        return field_ids

    def has_field(self, field_id):
        """Return true if a field_id is present."""
        return field_id in self._field_ids

    def field_meta(self, field_id):
        """Return full metadata for a field."""
        if not self.has_field(field_id):
            return False
        meta = {key: value for key, value in self._field_list[field_id].items()}
        if meta.get('parent'):
            meta = self.add_parent_meta(meta, meta['parent'])
        return meta

    def field_parent_list(self, field_id):
        """Return list of parent fields for a field."""
        parents = []
        meta = self.field_meta(field_id)
        if meta.get('parent'):
            parent_meta = self.field_meta(meta['parent'])
            parents.append({'id': meta['parent']})
            for key, value in parent_meta.items():
                if key not in ('field_id', 'children', 'data'):
                    parents[-1].update({key: value})
            if 'children' in parent_meta:
                parents.append('children')
            elif 'data' in parent_meta:
                parents.append('data')
            parents = self.field_parent_list(meta['parent']) + parents
        return parents

    def add_parents(self, parents):
        """Add field metadata."""
        fields = self.fields
        if not parents:
            return fields
        parent = self._field_list
        for required in parents:
            if isinstance(required, dict):
                if isinstance(parent, dict):
                    if required['id'] not in parent:
                        parent.update({required['id']: required})
                        fields.append(required)
                    else:
                        for key in required.keys():
                            if key not in ['children', 'data']:
                                parent[required['id']][key] = required[key]
                    parent = parent[required['id']]
                elif required['id'] in self._field_list:
                    for key in required.keys():
                        if key not in ['children', 'data']:
                            self._field_list[required['id']][key] = required[key]
                    parent = self._field_list[required['id']]
                elif isinstance(parent, list):
                    try:
                        index = next(i for i, field in enumerate(parent)
                                     if field['id'] == required['id'])
                        parent = parent[index]
                    except StopIteration:
                        parent.append(required)
                        parent = required
            else:
                if required not in parent:
                    parent.update({required: []})
                parent = parent[required]
        return parent

    def add_field(self, parents=None, **kwargs):
        """Add field metadata."""
        if parents is None:
            parents = []
        parent = self.add_parents(parents)
        if self.has_field(kwargs['field_id']):
            meta = self._field_list[kwargs['field_id']]
        else:
            index = next((i for (i, d) in enumerate(parent) if d['id'] == kwargs['field_id']), None)
            if index is not None:
                meta = parent[index]
            else:
                meta = {}
                parent.append(meta)
        for key, value in kwargs.items():
            if key == 'field_id':
                key = 'id'
            meta[key] = value
        # if parents:
        #     meta['parents'] = parents

    def to_dict(self):
        """Create a dict of metadata."""
        data = {}
        for key in self.__slots__:
            if not key.startswith('_'):
                if hasattr(self, key):
                    if key == 'dataset_id':
                        data['id'] = getattr(self, key)
                    else:
                        data[key] = getattr(self, key)
        return data

    @staticmethod
    def _list_fields(parent, fields=None, parent_id=None):
        """Create a dict of fields."""
        if fields is None:
            fields = {}
        for field in parent:
            if parent_id:
                field.update({'parent': parent_id})
            fields.update({field['id']: field})
            if 'children' in field:
                Metadata._list_fields(field['children'], fields, field['id'])
            if 'data' in field:
                Metadata._list_fields(field['data'], fields, field['id'])
        return fields

    def add_parent_meta(self, meta, parent_id):
        """Add parent metadata to field metadata."""
        parent_meta = self.field_meta(parent_id)
        for key, value in parent_meta.items():
            if key not in list(meta.keys()) + ['children', 'data']:
                meta.update({key: value})
        if parent_meta.get('parent'):
            meta = self.add_parent_meta(meta, parent_meta['parent'])
        return meta


if __name__ == '__main__':
    import doctest
    doctest.testmod()