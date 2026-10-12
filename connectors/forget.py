"""Operator utility: scrub a Person entity from a snapshot, not free-text identity references."""
import argparse
import hashlib
import json
from pathlib import Path
from graph.ingestion import validate_snapshot

def main():
    p=argparse.ArgumentParser(description='Remove a Person node and its edges from an exported public snapshot')
    p.add_argument('person_id')
    p.add_argument('--snapshot',default='data/falkordb/snapshot.json')
    args=p.parse_args()
    path=Path(args.snapshot); raw=json.loads(path.read_text()); validate_snapshot(raw)
    person=next((n for n in raw['nodes'] if n['id']==args.person_id and n['type']=='Person'),None)
    if not person: p.error('Person node not found in snapshot')
    raw['nodes']=[n for n in raw['nodes'] if n['id']!=args.person_id]
    raw['edges']=[e for e in raw['edges'] if args.person_id not in (e['source'],e['target'])]
    raw['suppressed']=sorted(set(raw.get('suppressed',[]))|{hashlib.sha256(args.person_id.encode()).hexdigest()})
    validate_snapshot(raw)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(raw,indent=2,ensure_ascii=False));temp.replace(path)
    print('Person node and edges removed. Review free-text mentions, other snapshot copies, Git history, and hosted data separately.')
if __name__=='__main__': main()
