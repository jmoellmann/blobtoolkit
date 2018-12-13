#!/usr/bin/env python3

# pylint: disable=too-many-locals,too-many-branches

"""Parse BLAST results into MultiArray Field."""

from collections import defaultdict
import file_io
from field import Category, MultiArray, Variable


def parse_blast(blast_file, results=None):
    """Parse file into dict of lists."""
    if results is None:
        results = defaultdict(list)
    for line in file_io.stream_file(blast_file):
        row = line.rstrip().split('\t')
        seq_id, *offset = row[0].split('_-_')
        offset = int(offset[0]) if offset else 0
        try:
            hit = {'subject': row[4],
                   'score': float(row[2]),
                   'start': int(row[9])+offset,
                   'end': int(row[10])+offset}
        except IndexError:
            hit = {'subject': row[3],
                   'score': float(row[2]),
                   'start': None,
                   'end': None}
        try:
            hit.update({'taxid': int(row[1])})
        except ValueError:
            hit.update({'taxid': 0})
        results[seq_id].append(hit)
    return results


def apply_taxrule(blast, taxdump, taxrule, identifiers, results=None):
    """Apply taxrule to parsed BLAST results."""
    if results is None:
        blank = [None] * len(identifiers.values)
        results = [
            {'field_id': "%s_%s" % (taxrule, rank), 'values': blank[:], 'data': {
                'cindex': blank[:], 'score': blank[:], 'positions': blank[:],
                'hits': blank[:]
            }}
            for rank in taxdump.list_ranks()
        ]
    values = [{
        'category': defaultdict(str),
        'cindex': defaultdict(int),
        'score': defaultdict(float),
        'positions': defaultdict(list),
        'hits': defaultdict(list)
        } for rank in taxdump.list_ranks()]
    for seq_id, hits in blast.items():
        sorted_hits = sorted(hits, key=lambda k: k['score'], reverse=True)
        for index, rank in enumerate(taxdump.list_ranks()):
            cat_scores = defaultdict(float)
            for hit in sorted_hits:
                try:
                    category = taxdump.ancestors[hit['taxid']][rank]
                except KeyError:
                    category = 0
                if category > 0:
                    category = taxdump.names[category]
                elif category < 0:
                    category = "%s-undef" % taxdump.names[-category]
                else:
                    category = 'no-hit'
                values[index]['positions'][seq_id].append(
                    [category]
                )
                if index == 0:
                    values[index]['hits'][seq_id].append(
                        [hit['taxid'], hit['start'], hit['end'], hit['score'], hit['subject']]
                        )
                if len(values[index]['positions'][seq_id]) < 10:
                    cat_scores[category] += hit['score']
            top_cat = max(cat_scores, key=cat_scores.get)
            values[index]['category'][seq_id] = top_cat
            values[index]['score'][seq_id] = cat_scores.get(top_cat)
            values[index]['cindex'][seq_id] = len(cat_scores.keys()) - 1
    for index, rank in enumerate(taxdump.list_ranks()):
        if not identifiers.validate_list(list(values[index]['category'].keys())):
            raise UserWarning('Contig names in the hits file do not match dataset identifiers.')
        for i, seq_id in enumerate(identifiers.values):
            if results[index]['data']['score'][i] in (0, None):
                if seq_id in values[index]['category']:
                    results[index]['values'][i] = values[index]['category'][seq_id]
                    results[index]['data']['score'][i] = values[index]['score'][seq_id]
                    results[index]['data']['cindex'][i] = values[index]['cindex'][seq_id]
                    results[index]['data']['positions'][i] = values[index]['positions'][seq_id]
                    if index == 0:
                        results[index]['data']['hits'][i] = values[index]['hits'][seq_id]
                else:
                    results[index]['values'][i] = 'no-hit'
                    results[index]['data']['score'][i] = 0
                    results[index]['data']['cindex'][i] = 0
                    results[index]['data']['positions'][i] = []
                    if index == 0:
                        results[index]['data']['hits'][i] = []
    return results


def create_fields(results, taxrule, files, fields=None):
    """Store BLAST results as Fields."""
    if fields is None:
        fields = []
    hits_id = "%s_%s" % (taxrule, 'positions')
    fields.append(MultiArray(hits_id,
                             values=results[0]['data']['hits'],
                             meta={
                                 'field_id': hits_id,
                                 'name': hits_id,
                                 'type': 'multiarray',
                                 'datatype': 'mixed',
                                 'preload': False,
                                 'active': False,
                                 'files': files
                                 },
                             parents=['children', {'id': taxrule}, 'children'],
                             category_slot=None,
                             headers=['taxid', 'start', 'end', 'score', 'subject']))
    for result in results:
        main = Category(result['field_id'],
                        values=result['values'],
                        meta={
                            'field_id': result['field_id'],
                            'name': result['field_id']
                        },
                        parents=['children', {'id': taxrule}, 'children'])
        fields.append(main)
        parents = ['children', {'id': taxrule}, 'children', {'id': result['field_id']}, 'data']
        field_id = "%s_%s" % (result['field_id'], 'cindex')
        fields.append(Variable(field_id,
                               values=result['data']['cindex'],
                               meta={
                                   'scale': 'scaleLinear',
                                   'field_id': field_id,
                                   'name': field_id,
                                   'datatype': 'integer',
                                   'range': [min(result['data']['cindex']),
                                             max(result['data']['cindex'])],
                                   'preload': False,
                                   'active': False
                                   },
                               parents=parents))
        field_id = "%s_%s" % (result['field_id'], 'score')
        _min = min(result['data']['score'])
        fields.append(Variable(field_id,
                               values=result['data']['score'],
                               meta={
                                   'scale': 'scaleLog',
                                   'field_id': field_id,
                                   'name': field_id,
                                   'clamp': 1 if _min == 0 else False,
                                   'datatype': 'float',
                                   'range': [_min,
                                             max(result['data']['score'])],
                                   'preload': False,
                                   'active': False
                                   },
                               parents=parents))
        subfield = 'positions'
        field_id = "%s_%s" % (result['field_id'], subfield)
        fields.append(MultiArray(field_id,
                                 values=result['data'][subfield],
                                 fixed_keys=main.keys,
                                 meta={
                                     'field_id': field_id,
                                     'name': field_id,
                                     'type': 'multiarray',
                                     'datatype': 'string',
                                     'preload': False,
                                     'active': False,
                                     'linked_field': hits_id
                                     },
                                 parents=parents,
                                 category_slot=0,
                                 headers=['name']))
    return fields


def parse(files, **kwargs):
    """Parse BLAST results into Fields."""
    blast = None
    fields = []
    identifiers = kwargs['dependencies']['identifiers']
    if kwargs['--taxrule'] == 'bestsum':
        for file in files:
            blast = parse_blast(file, blast)
        results = apply_taxrule(blast, kwargs['taxdump'], kwargs['--taxrule'], identifiers)
        fields = create_fields(results, kwargs['--taxrule'], files)
    elif kwargs['--taxrule'] == 'bestsumorder':
        results = None
        for file in files:
            blast = parse_blast(file)
            results = apply_taxrule(blast,
                                    kwargs['taxdump'],
                                    kwargs['--taxrule'],
                                    identifiers,
                                    results)
        fields = create_fields(results, kwargs['--taxrule'], files)
    if 'cat' not in kwargs['meta'].plot:
        kwargs['meta'].plot.update({'cat': "%s_phylum" % kwargs['--taxrule']})
    return fields


def parent():
    """Set standard metadata for BLAST."""
    blast = {
        'datatype': 'string',
        'type': 'category',
        'id': 'taxonomy',
        'name': 'Taxonomy'
    }
    return [
        blast
    ]