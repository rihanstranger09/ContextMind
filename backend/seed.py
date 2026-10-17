"""Run: python -m backend.seed (uses .env, seeds empty isolated graphs)."""
from graph.store import Store


def main():
    for workspace in ('novapay', 'falkordb'):
        graph = Store(backend='falkordb', workspace=workspace)
        assert graph.get('sys_database' if workspace == 'novapay' else 'org_falkordb')
        print(f'{workspace}: native FalkorDB ready; {graph.counts()}')


if __name__ == '__main__':
    main()
