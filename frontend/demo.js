const liveLink = document.querySelector('#live-url');
if (location.protocol === 'http:' || location.protocol === 'https:') {
  liveLink.textContent = location.origin;
  liveLink.href = location.origin + '/dashboard';
}
(async () => {
  const status = document.querySelector('#health');
  try {
    const response = await fetch('/api/health', {cache: 'no-store', signal: AbortSignal.timeout(10000)});
    const health = await response.json();
    if (!response.ok || health.status !== 'healthy') throw new Error('Unhealthy service');
    status.textContent = `Healthy · ${health.version} · Graph mode: ${health.graph_mode} · Sample data: ${health.sample_data}`;
  } catch {
    status.textContent = 'Health check failed. Serve this page through ContextMind and check /api/health before presenting the demo.';
  }
})();
