
from smart_agri.core.platform_metrics import PlatformMetricsRegistry
from smart_agri.core.observability import render_prometheus_metrics


def test_platform_metrics_snapshot_contains_average_response():
    registry = PlatformMetricsRegistry()
    registry.record('/api/health/', 'GET', 200, 50)
    registry.record('/api/health/', 'GET', 200, 70)
    snapshot = registry.snapshot()
    assert snapshot['requests']['GET /api/health/'] == 2
    assert snapshot['average_response_ms']['GET /api/health/'] == 60


def test_render_prometheus_metrics_includes_metric_names(monkeypatch):
    from smart_agri.core import observability

    class DummyMetrics:
        def snapshot(self):
            return {
                'requests': {'GET /api/health/': 3},
                'status_codes': {'200': 3},
                'average_response_ms': {'GET /api/health/': 12},
            }

    monkeypatch.setattr(observability, 'platform_metrics', DummyMetrics())
    text = render_prometheus_metrics()
    assert 'agriasset_http_requests_total' in text
    assert 'agriasset_http_status_total' in text


def test_render_prometheus_metrics_includes_outbox_metrics(monkeypatch):
    from smart_agri.core import observability

    class DummyMetrics:
        def snapshot(self):
            return {
                'requests': {},
                'status_codes': {},
                'average_response_ms': {},
            }

    monkeypatch.setattr(observability, 'platform_metrics', DummyMetrics())
    monkeypatch.setattr(observability, 'persistent_outbox_snapshot', lambda: {'counts': {'pending': 2}, 'locked_count': 1, 'retry_ready_count': 2})
    text = render_prometheus_metrics()
    assert 'agriasset_outbox_events' in text
    assert 'agriasset_outbox_locked_events' in text
