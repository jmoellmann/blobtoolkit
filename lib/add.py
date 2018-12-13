#!/usr/bin/env python3

# pylint: disable=no-member, too-many-branches

"""
Add data to a BlobDir.

Usage:
    blobtools add [--busco TSV...] [--cov BAM...]  [--hits TSV...]  [--fasta FASTA]
                  [--key path=value...] [--link path=url...] [--skip-link-test]
                  [--blobdb JSON] [--meta YAML] [--synonyms TSV...]
                  [--taxdump DIRECTORY] [--taxrule bestsum|bestsumorder]
                  [--threads INT] [--pileup-args key=value...] [--create] [--replace] DIRECTORY

Arguments:
    DIRECTORY             Existing Blob directory.

Options:
    --busco TSV           BUSCO full_table.tsv output file.
    --cov BAM             BAM/SAM/CRAM read alignment file.
    --fasta FASTA         FASTA sequence file.
    --hits TSV            Tabular BLAST/Diamond output file.
    --key path=value      Set a metadata key to value.
    --link path=URL       Link to an external resource.
    --skip-link-test      Skip test to see if link URL can be resolved.
    --meta YAML           Dataset metadata.
    --blobdb JSON         Blobtools v1 blobDB.
    --synonyms TSV        TSV file containing current identifiers and synonyms.
    --taxdump DIRECTORY   Location of NCBI new_taxdump directory.
    --taxrule bestsum|bestsumorder
                          Rule to use when assigning BLAST hits to taxa. [Default: bestsum]
    --threads INT         Number of threads to use for multithreaded tasks. [Default: 1]
    --pileup-args key=val Key/value pairs to pass to samtools pileup.
    --create              Create a new BlobDir.
    --replace             Replace existing fields with matching ids.

Examples:
    # 1. Add BUSCO scores to BlobDir
    ./blobtools add --busco busco.full_table.tsv BlobDir

"""

from docopt import docopt
import file_io
import blob_db
import busco
import cov
import fasta
import hits
import key
import link
import synonyms
from field import Identifier
from fetch import fetch_field, fetch_metadata, fetch_taxdump

FIELDS = [{'flag': '--fasta', 'module': fasta, 'depends': ['identifiers']},
          {'flag': '--blobdb', 'module': blob_db, 'depends': ['identifiers']},
          {'flag': '--busco', 'module': busco, 'depends': ['identifiers']},
          {'flag': '--cov', 'module': cov, 'depends': ['identifiers', 'length', 'ncount']},
          {'flag': '--hits', 'module': hits, 'depends': ['identifiers']},
          {'flag': '--synonyms', 'module': synonyms, 'depends': ['identifiers']}]
PARAMS = set(['--taxrule', '--threads', '--pileup-args'])


def has_field_warning(meta, field_id):
    """Warn if dataset has existing field with same id."""
    if meta.has_field(field_id):
        print("WARN: Field \'%s\' is already present in dataset, not overwriting." % field_id)
        print("WARN: Use '--replace' flag to overwrite existing field.")
        return 1
    return 0


def main():
    """Entrypoint for blobtools add."""
    args = docopt(__doc__)
    meta = fetch_metadata(args['DIRECTORY'], **args)
    if args['--fasta']:
        meta.assembly.update({'file': args['--fasta']})
    taxdump = None
    dependencies = {}
    for field in FIELDS:
        if args[field['flag']]:
            for dep in field['depends']:
                if dep not in dependencies or not dependencies[dep]:
                    dependencies[dep] = fetch_field(args['DIRECTORY'], dep, meta)
            if field['flag'] == '--hits':
                if not taxdump:
                    taxdump = fetch_taxdump(args['--taxdump'])
            parents = field['module'].parent()
            parsed = field['module'].parse(
                args[field['flag']],
                **{key: args[key] for key in PARAMS},
                taxdump=taxdump,
                dependencies=dependencies,
                meta=meta)
            if not isinstance(parsed, list):
                parsed = [parsed]
            for data in parsed:
                if not args['--replace']:
                    if has_field_warning(meta, data.field_id):
                        continue
                meta.add_field(parents+data.parents, **data.meta)
                if isinstance(data, Identifier):
                    meta.records = len(data.values)
                json_file = "%s/%s.json" % (args['DIRECTORY'], data.field_id)
                file_io.write_file(json_file, data.values_to_dict())
                dependencies[data.field_id] = data
    if 'identifiers' not in dependencies:
        dependencies['identifiers'] = fetch_field(args['DIRECTORY'], 'identifiers', meta)
    for string in args['--link']:
        link.add(string, meta, dependencies['identifiers'].values, args['--skip-link-test'])
    for string in args['--key']:
        key.add(string, meta)
    file_io.write_file("%s/meta.json" % args['DIRECTORY'], meta.to_dict())


if __name__ == '__main__':
    main()