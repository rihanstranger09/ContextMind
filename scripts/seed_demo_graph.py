"""Create fresh, isolated native graphs for filming without deleting existing data.

Requires a running FalkorDB and connection settings from the local shell. Does
not print or write credentials; the generated graph prefix is not a secret.
"""
import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def seed(output):
    if os.getenv('GRAPH_BACKEND') != 'falkordb':
        raise SystemExit('Refusing to seed a native recording: set GRAPH_BACKEND=falkordb')
    prefix = 'contextmind_recording_' + uuid4().hex[:12]
    os.environ['FALKOR_GRAPH'] = prefix
    from graph.store import Store
    from graph.showcase import graph_showcase, company_showcase
    try:
        company = Store('falkordb', workspace='novapay')
        public = Store('falkordb', workspace='falkordb')
        if not company_showcase(company)['native_cypher_executed'] or not graph_showcase(public)['native_cypher_executed']:
            raise RuntimeError('Native proof unavailable')
    except Exception:
        # Driver exceptions can contain endpoint details; do not echo them.
        raise SystemExit('Native seed/proof unavailable; check private connection settings locally') from None
    if company.get('ticket_video_abcd1234'):
        raise SystemExit('Recording ticket already exists; choose another disposable graph')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('FALKOR_GRAPH=' + prefix + '\n', encoding='utf-8')
    print('Created isolated native recording graphs; prefix stored in ' + str(output))
    print('Company entities:', company.counts()['nodes'], 'Public entities:', public.counts()['nodes'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-out', default='.runtime/recording-graph.env', help='Ignored local file; graph name only')
    args = parser.parse_args()
    seed(args.env_out)
