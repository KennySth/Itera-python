"""
Internal reverse proxy for combined Render deployment.
Routes /api/core/* → Scala :8080 and /api/logic/* → Prolog :9000.
"""
import os
import logging
from fastapi import APIRouter, Request
from fastapi.responses import Response

import httpx

logger = logging.getLogger(__name__)

router = APIRouter()

SCALA_URL = f"http://127.0.0.1:{os.getenv('SCALA_PORT', '8080')}"
PROLOG_URL = f"http://127.0.0.1:{os.getenv('PROLOG_PORT', '9001')}"

_proxy_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)


async def _forward(target_base: str, path: str, request: Request) -> Response:
    """Forward request to an internal service and relay the response."""
    url = f"{target_base}{path}"
    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    try:
        resp = await _proxy_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
        # Filter hop-by-hop headers from response
        resp_headers = dict(resp.headers)
        for h in ("transfer-encoding", "connection", "content-encoding"):
            resp_headers.pop(h, None)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=resp_headers,
        )
    except httpx.ConnectError:
        logger.error("Proxy target unreachable: %s", url)
        return Response(
            content='{"error":"service_unavailable"}',
            status_code=503,
            media_type="application/json",
        )
    except Exception as e:
        logger.error("Proxy error: %s", e)
        return Response(
            content=f'{{"error":"proxy_error","detail":"{e}"}}',
            status_code=502,
            media_type="application/json",
        )


@router.api_route("/api/core/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_core(path: str, request: Request):
    """Proxy /api/core/* → Scala Play :8080 (preserves /api/core prefix)"""
    return await _forward(SCALA_URL, f"/api/core/{path}", request)


@router.api_route("/api/logic/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_logic(path: str, request: Request):
    """Proxy /api/logic/* → Prolog :9001 (strips /api/logic prefix)"""
    return await _forward(PROLOG_URL, f"/{path}", request)
