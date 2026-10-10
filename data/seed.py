"""Replay an offline public snapshot into the configured FalkorDB/demo backend."""
import argparse
import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph.store import Store
from graph.ingestion import replay

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--org',choices=['falkordb'],default='falkordb')
    parser.add_argument('--snapshot',default='data/falkordb/snapshot.json')
    args=parser.parse_args()
    s=Store(workspace=args.org,seed_path=args.snapshot)
    print(replay(s,args.snapshot))
if __name__=='__main__': main()
