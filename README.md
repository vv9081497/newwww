# Shopify Checkout API — Vercel Serverless

A serverless HTTP API that performs an end-to-end Shopify Checkout (GraphQL) + Credit Card Vaulting flow against any public Shopify store. Built to run on Vercel Python runtime.

## Endpoint

```
GET /api/shopify?site=<shopify_store_url>&cc=<num|mm|yyyy|cvv>&proxy=<optional>
```

A `/shopify` alias is also available (via `vercel.json` rewrite).

## Parameters

| Name   | Required | Description                                            | Example                |
|--------|----------|--------------------------------------------------------|------------------------|
| `site` | Yes      | Public Shopify store URL or bare domain                | `colourpop.com`        |
| `cc`   | Yes      | Card line in `number\|month\|year\|cvv` format          | `4242424242424242\|12\|2030\|123` |
| `proxy`| No       | HTTP/SOCKS proxy `host:port` (or full URL)             | `1.2.3.4:8080`         |

## Response

```json
{
  "status": "success",
  "site": "colourpop.com",
  "cc": "4242424242424242|12|2030|123",
  "proxy": null,
  "started_at": "2026-06-27T09:50:23Z",
  "elapsed_seconds": 10.25,
  "result": {
    "category": "DECLINED",
    "code": "SUBMISSION_REJECTED",
    "detail": "Payment submission was rejected: REJECTED: ARTIFACT_DISSATISFACTION"
  }
}
```

### Result categories

| Category   | Meaning                                            |
|------------|----------------------------------------------------|
| `CHARGED`  | Payment succeeded — receipt processed, order placed |
| `DECLINED` | Card or processor declined the payment              |
| `ERROR`    | Pipeline error (session init, no product, vault, etc.) |

## Deploy to Vercel

### Option A — One-click via Vercel CLI

```bash
npm i -g vercel
cd shopify-checkout-api
vercel              # preview deployment
vercel --prod       # production deployment
```

### Option B — Via GitHub

1. Push this repo to GitHub.
2. Go to https://vercel.com/new
3. Import the repository.
4. Vercel auto-detects Python (`@vercel/python` builder via `vercel.json`).
5. Click **Deploy**.

No environment variables required.

## Project structure

```
shopify-checkout-api/
├── api/
│   └── shopify.py            # Vercel serverless function entrypoint
├── lib/
│   ├── __init__.py
│   └── shopify_checker.py    # Framework-agnostic ShopifyChecker class
├── requirements.txt          # Python deps (just `requests`)
├── vercel.json               # Build config + /shopify rewrite + 300s timeout
├── README.md
└── .gitignore
```

## Run locally

### As a plain Flask app (for development)

```python
# dev_server.py
from flask import Flask, request, jsonify
from lib.shopify_checker import ShopifyChecker

app = Flask(__name__)

@app.route("/shopify")
def shopify_check():
    site = request.args.get("site")
    cc = request.args.get("cc")
    proxy = request.args.get("proxy")
    if not site or not cc:
        return jsonify({"status": "error", "message": "Missing site or cc"}), 400
    result = ShopifyChecker(base_url=site, proxy=proxy).check_card(cc)
    return jsonify({"status": "success", "site": site, "cc": cc, "result": result})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

```bash
pip install flask requests
python dev_server.py
```

### With Vercel CLI

```bash
npm i -g vercel
vercel dev    # serves /api/shopify and /shopify on localhost:3000
```

## Supported Shopify flow

1. `init_session` — fetches `/cart.js` to seed cookies (`_shopify_y`, `_shopify_s`)
2. `find_cheapest_product` — lists `/products.json` (fallback to `/collections/all`)
3. `create_checkout_session` — navigates `/cart/<variant>:1`, follows redirects, parses `serialized-sessionToken` and `serialized-graphql` meta tags
4. `vault_card` — POSTs card to `https://deposit.shopifycs.com/sessions` (Shopify's PCI-compliant vault)
5. `submit` — calls `submitForCompletion` GraphQL mutation against `/checkouts/unstable/graphql` with full buyer identity, delivery, and payment lines
6. `poll_receipt` — polls `receipt(receiptId:)` until `ProcessedReceipt` / `FailedReceipt`

## Notes

- Vercel Python serverless functions have a default 10s timeout on hobby tier; `vercel.json` requests 300s — verify your plan supports it.
- Bot-protected stores (Cloudflare, etc.) may return `CHECKOUT_FAILED` — use the `proxy` parameter.
- All 66 Shopify `PaymentErrorCode` values are mapped to human-readable descriptions inside `lib/shopify_checker.py`.
