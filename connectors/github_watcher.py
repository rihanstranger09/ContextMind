"""Opt-in bounded full refresh, not a commit stream. No watcher starts with the web app."""
import argparse
import os
import time
from datetime import datetime,timezone
from connectors.github import GitHub, collect
from graph.ingestion import replay
from graph.store import Store

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--org',choices=['falkordb'],default='falkordb')
    p.add_argument('--interval',type=int,default=900)
    p.add_argument('--output',default='.runtime/snapshots/falkordb.json')
    p.add_argument('--once',action='store_true')
    args=p.parse_args()
    if os.getenv('GRAPH_BACKEND')!='falkordb': p.error('Live sync requires GRAPH_BACKEND=falkordb; JSON demo changes require app restart')
    if args.interval<900: p.error('Minimum interval is 900 seconds')
    while True:
        try:
            snapshot=collect(GitHub(),args.output)
            replay(Store(workspace='falkordb',seed_path=args.output),args.output)
            print(datetime.now(timezone.utc).isoformat(),'snapshot refreshed',len(snapshot['nodes']),flush=True)
        except Exception as e:
            print('Refresh failed; last collected snapshot retained:',type(e).__name__,flush=True)
            if args.once: raise
        if args.once: break
        time.sleep(args.interval)
if __name__=='__main__': main()
