import argparse
from connectors.github import GitHub, collect

def main():
    parser=argparse.ArgumentParser(description='Collect a bounded, public-only FalkorDB GitHub snapshot')
    parser.add_argument('--org',choices=['falkordb'],default='falkordb')
    parser.add_argument('--source',choices=['github'],default='github')
    parser.add_argument('--output',default='data/falkordb/snapshot.json')
    args=parser.parse_args()
    snapshot=collect(GitHub(),args.output)
    print(f"Published {len(snapshot['nodes'])} nodes / {len(snapshot['edges'])} edges to {args.output}")
if __name__=='__main__': main()
