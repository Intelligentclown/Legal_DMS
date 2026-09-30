"""T146: CORS transport compatibility for the existing DocumentVersion
browser/Electron contract.

Kept as its own module rather than appended to T78's
`test_cors_configuration.py`, which remains the record of the wildcard
tightening that predates T146. This file is the record of the three headers
T146 adds to that same narrow allowlist, and -- just as importantly -- of
what T146 did *not* do: the allowlist is still explicit, an unrelated header
is still denied, and origin/credentials policy is unchanged.

Follows the same isolated `create_app()` + `TestClient` pattern T78's suite
established (the shared module-level app singleton cannot serve a
preflight-shaped request).
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient

from app.infrastructure.config.settings import Settings
from app.main import create_app

_ORIGIN = "http://localhost:5173"
_UPLOAD_PATH = "/api/v1/matter-types"

# The exact request headers a browser/Electron renderer sends for the
# already-existing DocumentVersion upload contract: the raw body, its
# content type, the required filename header, the bearer token, and the
# already-supported optional idempotency key.
_UPLOAD_REQUEST_HEADERS = "content-type, authorization, x-filename, idempotency-key"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    settings = Settings(_env_file=None, jwt_secret_key="test-secret", cors_origins=[_ORIGIN])
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    app: FastAPI = create_app()

    @app.get("/__t146_probe")
    def probe() -> Response:
        """Stands in for the existing download route's response shape so the
        real middleware can be exercised without standing up the full
        DocumentVersion write path (covered by T142's own suite)."""
        return Response(
            content=b"bytes",
            media_type="application/octet-stream",
            headers={"Content-Disposition": 'attachment; filename="report.pdf"'},
        )

    return TestClient(app)


def _preflight(
    client: TestClient, *, method: str, headers: str | None = None, path: str = "/api/v1/health"
) -> httpx.Response:
    request_headers = {"Origin": _ORIGIN, "Access-Control-Request-Method": method}
    if headers is not None:
        request_headers["Access-Control-Request-Headers"] = headers
    return client.options(path, headers=request_headers)


def _allowed(response: httpx.Response) -> set[str]:
    """Lower-cased allowlist, so assertions do not depend on Starlette's
    header-name casing."""
    return {
        value.strip().lower()
        for value in response.headers["access-control-allow-headers"].split(",")
    }


# Starlette's CORS middleware always adds the CORS-safelisted request headers
# to its preflight response, independent of this application's own
# `allow_headers` list. They are framework behaviour, not a widening of this
# application's policy -- `Access-Control-Request-Headers` naming any of them
# is accepted whether or not T146's list mentions them.
_STARLETTE_SAFELISTED = {"accept", "accept-language", "content-language"}
_T146_ALLOWLIST = {"content-type", "authorization", "x-filename", "idempotency-key"}


def test_upload_preflight_permits_the_whole_existing_upload_contract(
    client: TestClient,
) -> None:
    """All four headers the existing upload route needs, in one preflight --
    the request a browser actually sends."""
    response = _preflight(client, method="POST", headers=_UPLOAD_REQUEST_HEADERS)

    assert response.status_code == 200
    assert _allowed(response) >= _T146_ALLOWLIST


@pytest.mark.parametrize(
    "header", ["Content-Type", "Authorization", "X-Filename", "Idempotency-Key"]
)
def test_each_authorized_upload_header_is_permitted_individually(
    client: TestClient, header: str
) -> None:
    response = _preflight(client, method="POST", headers=header)

    assert response.status_code == 200
    assert header.lower() in _allowed(response)


def test_download_preflight_permits_its_request_headers(client: TestClient) -> None:
    """The download route needs nothing beyond `Authorization`; this proves
    the added headers did not come at the cost of the existing two."""
    response = _preflight(client, method="GET", headers="authorization")

    assert response.status_code == 200
    assert "authorization" in _allowed(response)


def test_content_disposition_is_exposed_to_the_browser(client: TestClient) -> None:
    response = client.get("/__t146_probe", headers={"Origin": _ORIGIN})

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="report.pdf"'
    exposed = [
        value.strip().lower()
        for value in response.headers["access-control-expose-headers"].split(",")
    ]
    assert "content-disposition" in exposed


@pytest.mark.parametrize(
    "header",
    [
        "X-Custom-Header",
        "X-Requested-With",
        "X-Organization-Id",
        "Cookie",
        "Origin-Lock",
    ],
)
def test_unrelated_non_allowlisted_request_headers_remain_denied(
    client: TestClient, header: str
) -> None:
    """The policy is still a narrow explicit allowlist, not a wildcard."""
    response = _preflight(client, method="POST", headers=header)

    assert response.status_code == 400
    assert response.text == "Disallowed CORS headers"


def test_allowed_header_list_contains_nothing_beyond_the_narrow_allowlist(
    client: TestClient,
) -> None:
    response = _preflight(
        client, method="POST", headers="authorization, content-type, x-filename, idempotency-key"
    )

    assert response.status_code == 200
    assert _allowed(response) == _T146_ALLOWLIST | _STARLETTE_SAFELISTED


def test_exposed_response_header_list_contains_only_content_disposition(
    client: TestClient,
) -> None:
    response = client.get("/__t146_probe", headers={"Origin": _ORIGIN})

    exposed = {
        value.strip().lower()
        for value in response.headers["access-control-expose-headers"].split(",")
    }
    assert exposed == {"content-disposition"}


def test_disallowed_method_is_still_rejected(client: TestClient) -> None:
    response = _preflight(client, method="TRACE")

    assert response.status_code == 400
    assert response.text == "Disallowed CORS method"


def test_origin_and_credentials_policy_is_unchanged(client: TestClient) -> None:
    """Origin allowlist and `allow_credentials` are exactly as T78 left them:
    the configured origin is echoed, an unconfigured one is not."""
    allowed = client.get("/api/v1/health", headers={"Origin": _ORIGIN})
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == _ORIGIN
    assert allowed.headers["access-control-allow-credentials"] == "true"

    denied = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert denied.status_code == 200
    assert "access-control-allow-origin" not in denied.headers


def test_upload_preflight_against_a_real_upload_path_is_permitted(client: TestClient) -> None:
    """Preflight is path-independent for the middleware, but the real upload
    path is what a renderer actually preflights, so it is exercised by name."""
    response = _preflight(
        client,
        method="POST",
        headers=_UPLOAD_REQUEST_HEADERS,
        path="/api/v1/matters/00000000-0000-0000-0000-000000000001/files/"
        "00000000-0000-0000-0000-000000000002/documents/"
        "00000000-0000-0000-0000-000000000003/versions",
    )

    assert response.status_code == 200
    assert _allowed(response) == _T146_ALLOWLIST | _STARLETTE_SAFELISTED
