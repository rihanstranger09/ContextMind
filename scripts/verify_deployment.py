"""Verify a deployed ContextMind instance end to end (standard library only).

Usage:
    python scripts/verify_deployment.py https://<deployment-host>
    CONTEXTMIND_BASE_URL=https://<deployment-host> python scripts/verify_deployment.py

A deployment only passes when BOTH workspace health checks report a ready
native FalkorDB graph AND both fixed Cypher proof endpoints confirm native
execution with the seeded result shapes. JSON-preview (demo) deployments,
unreachable graphs and half-seeded graphs fail closed with exit code 1.
Nothing secret is sent or printed: only public GET endpoints are probed.

Cold starts may need to seed an empty distinct graph on first use, so the
whole check suite retries for a few minutes by default. Recording the demo
video is gated on this script printing PASS against the production URL;
see docs/deployment-vercel.md.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

MIN_PUBLIC_ENTITIES = 332
MIN_PUBLIC_RELATIONSHIPS = 378
COMPANY_EVIDENCE_ROWS = 4
PUBLIC_PROOF_PATHS = 3


def _fetch(url, timeout):
    request = urllib.request.Request(url, headers={'User-Agent': 'contextmind-verify/1'})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode('utf-8', 'replace')


def fetch_json(url, timeout=20):
    status, body = _fetch(url, timeout)
    try:
        return status, json.loads(body)
    except ValueError:
        return status, None


def fetch_text(url, timeout=20):
    return _fetch(url, timeout)


def run_checks(base_url, get_json=fetch_json, get_text=fetch_text):
    """Return [(name, ok, detail)]; fetchers are injectable for offline tests."""
    base = base_url.rstrip('/')
    results = []

    def check_health(name, workspace):
        status, data = get_json(f'{base}/api/health?workspace={workspace}')
        data = data or {}
        ok = (status == 200 and data.get('status') == 'healthy'
              and data.get('graph_mode') == 'falkordb'
              and data.get('workspace') == workspace
              and data.get('graph_ready', True) is True)
        detail = (f"http={status} status={data.get('status')} graph_mode={data.get('graph_mode')} "
                  f"graph_ready={data.get('graph_ready')}")
        results.append((name, ok, detail))

    check_health('health novapay (fictional workspace)', 'novapay')
    check_health('health falkordb (public snapshot workspace)', 'falkordb')

    status, proof = get_json(f'{base}/api/graph/company-proof?workspace=novapay')
    proof = proof or {}
    evidence = proof.get('evidence') or []
    ok = (status == 200 and proof.get('native_cypher_executed') is True
          and proof.get('backend') == 'falkordb'
          and len(evidence) == COMPANY_EVIDENCE_ROWS)
    results.append(('native Cypher company proof (decision BASED_ON x4)', ok,
                    f"http={status} native={proof.get('native_cypher_executed')} "
                    f"backend={proof.get('backend')} evidence_rows={len(evidence)}"))

    status, proof = get_json(f'{base}/api/graph/showcase?workspace=falkordb')
    proof = proof or {}
    paths = proof.get('paths') or []
    ok = (status == 200 and proof.get('native_cypher_executed') is True
          and proof.get('backend') == 'falkordb'
          and (proof.get('entity_count') or 0) >= MIN_PUBLIC_ENTITIES
          and (proof.get('relationship_count') or 0) >= MIN_PUBLIC_RELATIONSHIPS
          and len(paths) == PUBLIC_PROOF_PATHS)
    results.append(('native Cypher public proof (org -> Python client -> releases)', ok,
                    f"http={status} native={proof.get('native_cypher_executed')} "
                    f"backend={proof.get('backend')} entities={proof.get('entity_count')} "
                    f"relationships={proof.get('relationship_count')} paths={len(paths)}"))

    status, body = get_text(f'{base}/dashboard')
    ok = status == 200 and 'ContextMind' in (body or '')
    results.append(('dashboard serves', ok, f'http={status}'))

    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base_url', nargs='?', default=os.getenv('CONTEXTMIND_BASE_URL'),
                        help='Deployment origin, e.g. https://contextmind.example.app')
    parser.add_argument('--timeout', type=float, default=30, help='Per-request timeout seconds')
    parser.add_argument('--retries', type=int, default=12,
                        help='Full-suite attempts while a cold deployment seeds its graph')
    parser.add_argument('--retry-delay', type=float, default=15, help='Seconds between attempts')
    args = parser.parse_args(argv)
    if not args.base_url or not args.base_url.startswith(('http://', 'https://')):
        parser.error('Provide a deployment base URL (argument or CONTEXTMIND_BASE_URL)')

    get_json = lambda url: fetch_json(url, timeout=args.timeout)  # noqa: E731
    get_text = lambda url: fetch_text(url, timeout=args.timeout)  # noqa: E731
    results = []
    for attempt in range(1, max(args.retries, 1) + 1):
        results = run_checks(args.base_url, get_json, get_text)
        if all(ok for _, ok, _ in results):
            break
        if attempt < args.retries:
            failed = sum(1 for _, ok, _ in results if not ok)
            print(f'Attempt {attempt}: {failed} check(s) not passing yet; '
                  f'retrying in {args.retry_delay:g}s (cold start / seeding) ...')
            time.sleep(args.retry_delay)

    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} -- {detail}")
    passed = all(ok for _, ok, _ in results)
    print('PASS deployment verified: native FalkorDB health + both Cypher proofs'
          if passed else
          'FAIL deployment NOT verified: do not record or present this URL as a native deployment')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
