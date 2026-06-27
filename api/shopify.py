# -*- coding: utf-8 -*-
"""
Vercel Python Serverless Function — Shopify Checkout API

Endpoint:  GET /api/shopify?site=<url>&cc=<num|mm|yyyy|cvv>&proxy=<optional>
           Also reachable at /shopify via the vercel.json rewrite.

Vercel Python runtime requires a `handler` class extending BaseHTTPRequestHandler.
"""

import sys
import os
import json
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Make the lib/ directory importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.shopify_checker import ShopifyChecker


def _json_response(handler, status_code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _process(site, cc, proxy):
    """Run the full Shopify checkout flow and return a structured result dict."""
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.time()
    try:
        checker = ShopifyChecker(base_url=site, proxy=proxy)
        result = checker.check_card(cc)
        return {
            "status": "success",
            "site": site,
            "cc": cc,
            "proxy": proxy or None,
            "started_at": started_at,
            "elapsed_seconds": round(time.time() - t0, 2),
            "result": {
                "category": result["category"],
                "code": result["code"],
                "detail": result["detail"],
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "site": site,
            "cc": cc,
            "proxy": proxy or None,
            "started_at": started_at,
            "elapsed_seconds": round(time.time() - t0, 2),
            "message": f"{type(e).__name__}: {e}",
        }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler for /api/shopify."""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        site = (qs.get("site", [None])[0] or "").strip()
        cc = (qs.get("cc", [None])[0] or "").strip()
        proxy = (qs.get("proxy", [None])[0] or "").strip() or None

        if not site or not cc:
            _json_response(
                self,
                400,
                {
                    "status": "error",
                    "message": "Missing required parameters. Usage: /api/shopify?site=<url>&cc=<num|mm|yyyy|cvv>&proxy=<optional>",
                },
            )
            return

        result = _process(site, cc, proxy)
        _json_response(self, 200, result)

    def log_message(self, format, *args):
        # Quiet logging in serverless context
        return
