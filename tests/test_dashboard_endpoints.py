"""Dashboard endpoint contract tests.

The growth endpoint previously returned a simulated curve - a decayed copy of
today's value plotted against a hardcoded Nifty level - for any user, including
one with no history at all. These tests pin the replacement behaviour: with
nothing to plot, plot nothing.
"""

import pytest


@pytest.mark.usefixtures("client")
class TestGrowthEndpoint:
    def test_a_user_with_no_holdings_gets_an_empty_series(self, client, auth_headers):
        """No history must yield no points, never a generated line."""
        response = client.get("/api/dashboard/growth", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_growth_requires_authentication(self, client):
        response = client.get("/api/dashboard/growth")

        assert response.status_code in (401, 403)


@pytest.mark.usefixtures("client")
class TestReturnsEndpoint:
    def test_metrics_are_null_when_they_cannot_be_computed(self, client, auth_headers):
        """A dash on the dashboard, not a plausible-looking number."""
        response = client.get("/api/dashboard/returns", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()

        assert body["xirr"] is None
        assert body["twr"] is None
        assert body["benchmark_return"] is None
        assert body["max_drawdown"] is None
        assert body["data_points"] == 0

    def test_returns_requires_authentication(self, client):
        response = client.get("/api/dashboard/returns")

        assert response.status_code in (401, 403)
