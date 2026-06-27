# -*- coding: utf-8 -*-
"""
Shopify Checkout API — Core Library
Updated June 2026 — supports Shopify's latest Checkout GraphQL + Credit Card Vaulting.

This module is framework-agnostic: it exposes the `ShopifyChecker` class which
can be wrapped by any HTTP handler (Flask, Vercel serverless, FastAPI, etc.).
"""

import uuid
import requests
import random
import json
import time
import re
import html
from urllib.parse import urlparse

# Updated Chrome UA strings (v134-137, early 2026)
_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]
_CH_UA_POOL = [
    '"Chromium";v="137", "Google Chrome";v="137", "Not=A?Brand";v="99"',
    '"Chromium";v="136", "Google Chrome";v="136", "Not=A?Brand";v="99"',
    '"Chromium";v="135", "Google Chrome";v="135", "Not=A?Brand";v="99"',
]
_PLATFORM_POOL = ['"Windows"', '"macOS"']

# All 66 PaymentErrorCode descriptions from Shopify's current schema
ERROR_DESCRIPTIONS = {
    "INCORRECT_NUMBER": "Card number does not comply with ISO/IEC 7812 numbering standard",
    "INVALID_NUMBER": "Card number was not matched by processor",
    "INVALID_EXPIRY_DATE": "Expiry date does not match correct formatting",
    "INVALID_CVC": "Security code does not match correct format (3-4 digits)",
    "EXPIRED_CARD": "Card number is expired",
    "INCORRECT_CVC": "Security code was not matched by the processor",
    "INCORRECT_ZIP": "Zip code is not in correct format",
    "INCORRECT_ADDRESS": "Billing address info was not matched by the processor",
    "INCORRECT_PIN": "Card PIN is incorrect",
    "NAME_MISMATCH": "Name on card and billing address don't match",
    "CARD_DECLINED": "Card number declined by processor",
    "PROCESSING_ERROR": "Processor error",
    "CALL_ISSUER": "Transaction requires voice authentication, call issuer",
    "PICK_UP_CARD": "Issuer requests that you pick up the card from the merchant",
    "CONFIG_ERROR": "Error in gateway or merchant configuration",
    "TEST_MODE_LIVE_CARD": "Card declined — request was in test mode, but used a non-test card",
    "UNSUPPORTED_FEATURE": "Gateway or merchant configuration does not support a feature used",
    "GENERIC_ERROR": "Unknown error during payment processing",
    "TRANSIENT_ERROR": "Infrastructure problem such as network or database connectivity",
    "GIFT_CARD_ERROR": "Error processing gift card payment",
    "REDEEMABLE_DISABLED": "The redeemable is disabled",
    "CUSTOM_REDEEMABLE_NO_LONGER_AVAILABLE": "Redeemable no longer available due to checkout change",
    "PAYMENT_METHOD_EXPIRED": "Payment method has expired",
    "AUTHENTICATION_ERROR": "Error during authentication",
    "AUTHORIZATION_ERROR": "Error during authorization",
    "UNKNOWN_PAYMENT_ERROR": "Unknown error during payment processing",
    "INVALID_PAYMENT_ERROR": "Invalid payment error during processing",
    "PUBLIC_PAYMENT_ERROR": "Payment could not be completed due to payment error",
    "UNPROCESSABLE_TRANSACTION": "Encountered an unprocessable transaction",
    "GATEWAY_NOT_ENABLED_ERROR": "Payment gateway is not enabled",
    "PAYPAL_RESTRICATED_ACCOUNT_GATEWAY": "Merchant's PayPal account is restricted",
    "MISSING_SHIPPING_ADDRESS": "Shipping address missing",
    "INVALID_SHIPPING_ADDRESS": "Shipping address is invalid",
    "FUNDING_ERROR": "Funding source failed",
    "UNILATERAL_AUTH_ERROR": "Unilateral accounts cannot do auth/capture, must do a sale",
    "INSUFFICIENT_FUNDS": "Customer account has insufficient funds",
    "INVALID_PAYMENT_METHOD": "Invalid payment method",
    "CANCELED_PAYPAL_BILLING_AGREEMENT": "PayPal billing agreement cancelled",
    "OFF_SESSION_REJECTED": "3DS off-session rejected",
    "AUTHENTICATION_REQUIRED": "Payment requires authentication",
    "TOKEN_EXPIRED": "Session expired — token no longer valid",
    "INVALID_TOKEN": "Token is invalid",
    "OAUTH_TOKEN_ERROR": "Unable to update OAuth token",
    "SUCCESSFUL_OFFSITE_WITH_GIFT_CARD_ERROR": "Offsite payment successful but gift card failed",
    "INVALID_BILLING_AGREEMENT_OR_TRANSACTION": "Billing agreement or transaction ID is invalid",
    "INVOICE_ALREADY_PAID": "Payment already made for this invoice",
    "INVALID_ITEM_TOTAL": "ItemTotal amount is not valid",
    "THIRD_PARTY_INTERNAL_ERROR": "Internal error on third party system",
    "INVALID_CURRENCY": "Transaction currency differs from previously specified",
    "CUSTOMER_NOT_FOUND": "Customer was not found",
    "CUSTOMER_IDENTIFIER_MISSING": "Customer identifier (email/phone) was missing",
    "AMOUNT_TOO_SMALL": "Transaction amount is too small",
    "PRE_CHARGE_ERROR": "Error validating payment information",
    "CONFIRMATION_REJECTED": "Shopify rejected the payment confirmation",
    "FRAUD_SUSPECTED": "Error that suggests fraud",
    "NO_ACCOUNT": "No account found for the payment provided",
    "INVALID_PURCHASE_TYPE": "Payment method not authorized for this purchase type",
    "PAYPAL_ERROR_GENERAL": "General PayPal error",
    "PAYMENT_ABOVE_THRESHOLD": "Payment amount above threshold for the region",
    "RISKY": "Payment rejected by risk control",
    "SHOP_PAY_DECLINED": "Payment declined by Shop Pay",
    "EXPIRED_BUYER_ACTION": "Buyer action has expired",
    "MOTO_TRANSACTIONS_BLOCKED": "MOTO transactions blocked for this merchant",
    "CANCELLED_PAYMENT": "Payment was cancelled",
    "CAPTCHA_REQUIRED": "Captcha required",
    "DECISION_RULE_BLOCK": "Declined due to decision rule block",
    "CVV_ATTEMPTS_EXCEEDED": "Too many failed CVV verification attempts",
    "INVALID_AMOUNT": "Amount too high or too low for provider",
    "INVALID_COUNTRY": "Payment method not available in customer's country",
    "PAYMENT_METHOD_UNAVAILABLE": "Payment method momentarily unavailable",
    "THREE_D_SECURE_FAILED": "3D Secure check failed",
}

def _rand_ua():       return random.choice(_UA_POOL)
def _rand_ch_ua():    return random.choice(_CH_UA_POOL)
def _rand_platform(): return random.choice(_PLATFORM_POOL)


def extract_meta(page_html, key):
    pattern = rf'<meta\s+name="serialized-{key}"\s+content="([^"]*)"'
    match = re.search(pattern, page_html, re.IGNORECASE)
    if not match:
        return None
    decoded = html.unescape(match.group(1))
    return decoded.strip('"')


def extract_serialized_graphql(page_html):
    pattern = r'<meta\s+name="serialized-graphql"\s+content="([^"]*?)"'
    match = re.search(pattern, page_html, re.IGNORECASE)
    if not match:
        return None
    try:
        decoded = html.unescape(match.group(1))
        cache = json.loads(decoded)
        for val in cache.values():
            if isinstance(val, dict) and 'session' in val:
                return val['session']
    except Exception:
        pass
    return None


class ShopifyChecker:
    SUBMIT_MUTATION = (
        "mutation s($input: NegotiationInput!, $attemptToken: String!) {\n"
        "  submitForCompletion(input: $input, attemptToken: $attemptToken) {\n"
        "    __typename\n"
        "    ... on SubmitSuccess { receipt { __typename ... on ProcessedReceipt { id orderIdentity { id } orderStatusPageUrl } ... on ProcessingReceipt { id pollDelay } ... on WaitingReceipt { id pollDelay } ... on FailedReceipt { id } } }\n"
        "    ... on SubmittedForCompletion { receipt { __typename ... on ProcessingReceipt { id pollDelay } ... on WaitingReceipt { id pollDelay } } }\n"
        "    ... on SubmitAlreadyAccepted { receipt { __typename } }\n"
        "    ... on SubmitFailed { reason }\n"
        "    ... on SubmitRejected { errors { code } }\n"
        "    ... on Throttled { pollAfter queueToken }\n"
        "    ... on CheckpointDenied { redirectUrl }\n"
        "    ... on TooManyRequests { retryAfter }\n"
        "  }\n"
        "}"
    )

    POLL_QUERY = (
        "query r($receiptId: ID) {\n"
        "  receipt(receiptId: $receiptId) {\n"
        "    __typename\n"
        "    ... on ProcessedReceipt { id orderIdentity { id } orderStatusPageUrl }\n"
        "    ... on ProcessingReceipt { id pollDelay }\n"
        "    ... on FailedReceipt { id }\n"
        "    ... on WaitingReceipt { id pollDelay }\n"
        "  }\n"
        "}"
    )

    def __init__(self, base_url, proxy=None):
        self.session = requests.Session()
        if proxy:
            p = proxy if proxy.startswith(("http", "socks")) else f"http://{proxy}"
            self.session.proxies = {"http": p, "https": p}
        self.base_url = base_url.rstrip("/")
        if not self.base_url.startswith("http"):
            self.base_url = "https://" + self.base_url
        _ua = _rand_ua()
        _cua = _rand_ch_ua()
        _pf = _rand_platform()
        self.headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=1, i",
            "sec-ch-ua": _cua,
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": _pf,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": _ua,
        }
        self.checkout_id = None
        self.variant_id = None
        self.product_id = None
        self.checkout_url = None
        self.session_token = None
        self.queue_token = None
        self.client_id = None
        self.visit_token = None
        self.shop_id = "0"
        self.cart_token = None
        self.payment_method_identifier = ""
        self.merchandise_lines = []
        self.stable_id = None
        self.price_amount = "0"
        self.currency_code = "USD"
        self.graphql_base = None
        self.failure_reason = ""

    def _random_address(self):
        fn = random.choice(["James","Mary","Robert","Patricia","John","Jennifer","Michael","Linda","David","Susan"])
        ln = random.choice(["Smith","Jones","Taylor","Brown","Williams","Wilson","Johnson","Davies","Miller","Davis"])
        st = f"{random.randint(100,9999)} {random.choice(['Maple St','Oak Ave','Washington Blvd','Lakeview Dr','Park Way','Broadway','Elm St','Pine Ave'])}"
        city, state, zp = random.choice([("Los Angeles","CA","90001"),("New York","NY","10001"),("Houston","TX","77001"),("Miami","FL","33101"),("Chicago","IL","60601"),("Phoenix","AZ","85001"),("Seattle","WA","98101")])
        return {"firstName": fn, "lastName": ln, "address1": st, "city": city, "zoneCode": state, "postalCode": zp, "countryCode": "US", "phone": f"+1703{random.randint(210,999)}{random.randint(1000,9999)}"}

    def init_session(self):
        try:
            r = self.session.get(f"{self.base_url}/cart.js", headers=self.headers, timeout=15)
            if r.status_code not in (200, 302):
                return False
        except Exception:
            return False
        self.client_id = self.session.cookies.get("_shopify_y") or self.session.cookies.get("shopify_client_id") or str(uuid.uuid4())
        self.visit_token = self.session.cookies.get("_shopify_s") or str(uuid.uuid4())
        try:
            self.cart_token = r.json().get("token", "")
        except Exception:
            self.cart_token = ""
        return True

    def find_cheapest_product(self):
        try:
            r = self.session.get(f"{self.base_url}/products.json", headers=self.headers, timeout=15)
            if r.status_code == 200:
                products = r.json().get("products", [])
                best = None
                low = float("inf")
                for p in products:
                    for v in p["variants"]:
                        if v.get("available") and float(v["price"]) < low:
                            low = float(v["price"])
                            best = v
                            self.product_id = p["id"]
                if best:
                    self.variant_id = best["id"]
                    return True
        except Exception:
            pass

        # Fallback: Search collections/all
        try:
            r = self.session.get(f"{self.base_url}/collections/all", headers=self.headers, timeout=15)
            if r.status_code == 200:
                handles = list(set(re.findall(r'/products/([a-zA-Z0-9\-]+)', r.text)))
                for handle in handles[:5]:
                    try:
                        pr = self.session.get(f"{self.base_url}/products/{handle}.js", headers=self.headers, timeout=10)
                        if pr.status_code == 200:
                            p_data = pr.json()
                            for v in p_data.get("variants", []):
                                if v.get("available"):
                                    self.variant_id = v["id"]
                                    self.product_id = p_data.get("id")
                                    return True
                    except Exception:
                        pass
        except Exception:
            pass

        return False

    def add_to_cart(self):
        return True

    def _monorail(self):
        url = f"{self.base_url}/.well-known/shopify/monorail/unstable/produce_batch"
        h = self.headers.copy()
        h.update({"content-type": "text/plain;charset=UTF-8", "origin": self.base_url, "priority": "u=4, i", "sec-fetch-mode": "no-cors"})
        now = int(time.time() * 1000)
        body = {"events": [{"schema_id": "storefront_customer_tracking/4.27", "payload": {"api_client_id": 580111, "event_id": f"sh-{str(uuid.uuid4()).upper()[:23]}", "event_name": "product_added_to_cart", "shop_id": int(self.shop_id or 0), "total_value": 47, "currency": "USD", "event_time": now, "event_source_url": self.checkout_url or self.base_url, "unique_token": self.client_id, "page_id": str(uuid.uuid4()).upper(), "source": "trekkie-storefront-renderer", "ccpa_enforced": True, "gdpr_enforced": False, "is_persistent_cookie": True, "analytics_allowed": True, "marketing_allowed": True, "sale_of_data_allowed": False, "preferences_allowed": True, "shopify_emitted": True}, "metadata": {"event_created_at_ms": now}}], "metadata": {"event_sent_at_ms": now}}
        try:
            self.session.post(url, data=json.dumps(body), headers=h, timeout=5)
        except Exception:
            pass

    def start_checkout(self):
        return True

    def extract_tokens(self):
        return True

    def create_checkout_session(self):
        cart_path = f"{self.variant_id}:1"
        url = f"{self.base_url}/cart/{cart_path}"

        headers = {
            'User-Agent': self.headers['user-agent'],
        }

        current_url = url
        r = None
        for _ in range(10):
            try:
                r = self.session.get(current_url, headers=headers, allow_redirects=False, timeout=15)
            except Exception:
                return False

            loc = r.headers.get('location')
            if r.status_code in (301, 302, 303, 307, 308) and loc:
                if loc.startswith('http'):
                    current_url = loc
                else:
                    parsed_base = urlparse(self.base_url)
                    current_url = f"{parsed_base.scheme}://{parsed_base.netloc}{loc}"
                continue
            break

        if r is None:
            return False

        self.checkout_url = current_url
        html_content = r.text

        # Extract sessionToken
        self.session_token = extract_meta(html_content, 'sessionToken')
        if not self.session_token:
            for pat in [
                r'name="serialized-sessionToken"\s+content="&quot;([^"]+)&quot;"',
                r'"sessionToken"\s*:\s*"(AAEB[^"]+)"',
                r"'sessionToken'\s*:\s*'(AAEB[^']+)'",
                r'(AAEB[A-Za-z0-9_\-]{30,})',
            ]:
                m = re.search(pat, html_content)
                if m:
                    self.session_token = m.group(1)
                    break

        if not self.session_token:
            return False

        # Extract serialized-graphql
        session_data = extract_serialized_graphql(html_content)
        if not session_data:
            return False

        negotiate = session_data.get("negotiate", {}).get("result", {})
        self.queue_token = negotiate.get("queueToken") or ""

        buyer = negotiate.get("buyerProposal", {})
        merchandise = buyer.get("merchandise", {})
        merch_lines = merchandise.get("merchandiseLines", [])

        self.merchandise_lines = []
        for ml in merch_lines:
            merch = ml.get("merchandise", {})
            total_val = ml.get("totalAmount", {}).get("value", {})
            qty_items = ml.get("quantity", {}).get("items", {})

            self.merchandise_lines.append({
                "stableId": ml.get("stableId", ""),
                "merchandiseId": merch.get("id", ""),
                "variantId": merch.get("variantId", ""),
                "quantity": qty_items.get("value") if qty_items.get("value") is not None else 1,
                "amount": total_val.get("amount", "0"),
                "currencyCode": total_val.get("currencyCode", "USD")
            })

        if self.merchandise_lines:
            self.stable_id = self.merchandise_lines[0]["stableId"]
            self.price_amount = self.merchandise_lines[0]["amount"]
            self.currency_code = self.merchandise_lines[0]["currencyCode"]
        else:
            self.stable_id = str(uuid.uuid4())
            self.price_amount = "0"
            self.currency_code = "USD"

        seller = negotiate.get("sellerProposal", {})
        payment = seller.get("payment", {})
        available_payment_lines = payment.get("availablePaymentLines", [])

        self.payment_method_identifier = ""
        for pl in available_payment_lines:
            pm = pl.get("paymentMethod", {})
            if pm.get("name") == "shopify_payments":
                self.payment_method_identifier = pm.get("paymentMethodIdentifier", "")
                break

        m = re.search(r"/checkouts/(cn/)?([a-zA-Z0-9]+)", self.checkout_url)
        if m:
            self.checkout_id = m.group(2)
        else:
            m = re.search(r"/[a-zA-Z0-9]{32}", self.checkout_url)
            self.checkout_id = m.group(0).strip('/') if m else str(uuid.uuid4()).replace('-', '')

        parsed = urlparse(self.checkout_url)
        if "shopify.com" in parsed.netloc and "checkout." in parsed.netloc:
            self.graphql_base = f"{parsed.scheme}://{parsed.netloc}"
        else:
            self.graphql_base = self.base_url

        return True

    def vault_card(self, cc_line):
        parts = cc_line.strip().split("|")
        if len(parts) != 4:
            return None, None
        card_num, month, year, cvv = [p.strip() for p in parts]
        addr = self._random_address()

        vault_url = "https://deposit.shopifycs.com/sessions"

        h = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": self.headers["user-agent"],
        }

        body = {
            "credit_card": {
                "number": card_num,
                "name": f"{addr['firstName']} {addr['lastName']}",
                "month": int(month),
                "year": int(year),
                "verification_value": cvv
            }
        }

        try:
            r = self.session.post(vault_url, json=body, headers=h, timeout=15)
            if r.status_code in (200, 201):
                return r.json().get("id"), addr
        except Exception:
            pass

        try:
            r = self.session.post("https://deposit.us.shopifycs.com/sessions", json=body, headers=h, timeout=15)
            if r.status_code in (200, 201):
                return r.json().get("id"), addr
        except Exception:
            pass

        return None, addr

    def submit(self, vault_id, addr, card_number=""):
        if not self.session_token:
            return None

        url = f"{self.graphql_base}/checkouts/unstable/graphql"
        h = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": self.headers["user-agent"],
            "origin": self.base_url,
            "referer": self.checkout_url,
            "x-checkout-one-session-token": self.session_token,
        }

        email = f"{addr['firstName'].lower()}{random.randint(10,99)}@gmail.com"

        merch_lines_payload = []
        for ml in self.merchandise_lines:
            merch_lines_payload.append({
                "stableId": ml["stableId"],
                "merchandise": {
                    "productVariantReference": {
                        "id": ml["merchandiseId"],
                        "variantId": ml["variantId"],
                        "properties": [],
                        "sellingPlanId": None
                    }
                },
                "quantity": {"items": {"value": ml["quantity"]}},
                "expectedTotalPrice": {
                    "value": {
                        "amount": ml["amount"],
                        "currencyCode": ml["currencyCode"]
                    }
                }
            })

        sa = {
            "firstName": addr["firstName"],
            "lastName": addr["lastName"],
            "address1": addr["address1"],
            "address2": addr.get("address2", ""),
            "city": addr["city"],
            "zoneCode": addr["zoneCode"],
            "countryCode": addr["countryCode"],
            "postalCode": addr["postalCode"],
            "phone": addr.get("phone", "")
        }

        billing_sa = {
            "firstName": addr["firstName"],
            "lastName": addr["lastName"],
            "address1": addr["address1"],
            "city": addr["city"],
            "zoneCode": addr["zoneCode"],
            "countryCode": addr["countryCode"],
            "postalCode": addr["postalCode"]
        }

        variables = {
            "attemptToken": str(uuid.uuid4()),
            "input": {
                "sessionInput": {"sessionToken": self.session_token},
                "queueToken": self.queue_token or None,
                "merchandise": {
                    "merchandiseLines": merch_lines_payload
                },
                "buyerIdentity": {
                    "email": email,
                    "customer": {
                        "presentmentCurrency": self.currency_code,
                        "countryCode": addr["countryCode"]
                    },
                    "phoneCountryCode": addr["countryCode"],
                    "marketingConsent": [],
                    "rememberMe": False
                },
                "delivery": {
                    "deliveryLines": [{
                        "selectedDeliveryStrategy": {
                            "deliveryStrategyMatchingConditions": {
                                "shipments": {"any": True},
                                "estimatedTimeInTransit": {"any": True}
                            }
                        },
                        "destination": {
                            "streetAddress": sa
                        },
                        "targetMerchandiseLines": {"any": True},
                        "expectedTotalPrice": {"any": True},
                        "deliveryMethodTypes": ["SHIPPING"]
                    }],
                    "noDeliveryRequired": []
                },
                "payment": {
                    "paymentLines": [{
                        "paymentMethod": {
                            "directPaymentMethod": {
                                "sessionId": vault_id,
                                "billingAddress": {"streetAddress": billing_sa},
                                "paymentMethodIdentifier": self.payment_method_identifier
                            }
                        },
                        "amount": {"any": True}
                    }],
                    "totalAmount": {"any": True}
                },
                "discounts": {"lines": [], "acceptUnexpectedDiscounts": True},
                "taxes": {"proposedTotalAmount": {"any": True}},
                "tip": {"tipLines": []},
                "note": {"message": "", "customAttributes": []},
                "localizationExtension": {"fields": []},
                "optionalDuties": {"buyerRefusesDuties": False},
                "cartMetafields": []
            }
        }

        payload = {
            "query": self.SUBMIT_MUTATION,
            "variables": variables
        }

        for attempt_num in range(12):
            try:
                r = self.session.post(url, json=payload, headers=h, timeout=20)
                res = r.json()
            except Exception:
                return None

            if "errors" in res and res.get("data") is None:
                return None

            sub = res.get("data", {}).get("submitForCompletion", {})
            tn = sub.get("__typename", "")

            if tn in ("SubmitSuccess", "SubmitAlreadyAccepted", "SubmittedForCompletion"):
                return sub.get("receipt", {}).get("id")
            elif tn == "SubmitFailed":
                self.failure_reason = sub.get("reason", "Unknown SubmitFailed")
                return None
            elif tn == "Throttled":
                self.queue_token = sub.get("queueToken", self.queue_token)
                payload["variables"]["input"]["queueToken"] = self.queue_token
                time.sleep(sub.get("pollAfter", 1000) / 1000.0)
            elif tn == "CheckpointDenied":
                self.failure_reason = "CAPTCHA_OR_CHECKPOINT_REQUIRED"
                return None
            elif tn in ("TooManyAttempts", "TooManyRequests"):
                self.failure_reason = "TOO_MANY_REQUESTS"
                return None
            elif tn == "SubmitRejected":
                codes = [e.get("code", "") for e in sub.get("errors", [])]
                self.failure_reason = f"REJECTED: {', '.join(codes)}"
                if "WAITING_PENDING_TERMS" in codes:
                    time.sleep(1.0)
                    continue
                return None
            else:
                time.sleep(1.0)
                if attempt_num < 11:
                    continue
                return None
        return None

    def poll_receipt(self, receipt_id):
        url = f"{self.graphql_base}/checkouts/unstable/graphql"
        h = {
            "accept": "application/json",
            "content-type": "application/json",
            "user-agent": self.headers["user-agent"],
            "origin": self.base_url,
            "referer": self.checkout_url,
            "x-checkout-one-session-token": self.session_token,
        }

        payload = {
            "query": self.POLL_QUERY,
            "variables": {"receiptId": receipt_id}
        }

        for i in range(15):
            try:
                r = self.session.post(url, json=payload, headers=h, timeout=15)
                receipt = r.json().get("data", {}).get("receipt", {})
                if not receipt:
                    time.sleep(2)
                    continue

                tn = receipt.get("__typename", "")

                if tn == "ProcessedReceipt":
                    order_id = receipt.get("orderIdentity", {}).get("id", "N/A")
                    return ("CHARGED", f"Order ID: {order_id}")

                elif tn == "FailedReceipt":
                    err = receipt.get("processingError", {})
                    code = err.get("code", "UNKNOWN")
                    desc = ERROR_DESCRIPTIONS.get(code, code)
                    return ("DECLINED", code, desc)

                elif tn in ("ProcessingReceipt", "WaitingReceipt"):
                    delay = receipt.get("pollDelay", 2000)
                    time.sleep(delay / 1000.0)
                    continue

            except Exception:
                pass
            time.sleep(2)

        return ("ERROR", "TIMEOUT", "Polling timed out")

    def check_card(self, cc_line):
        if not self.init_session():
            return {"category": "ERROR", "code": "SESSION_INIT_FAILED", "detail": "Could not initialize session with the store"}

        if not self.find_cheapest_product():
            return {"category": "ERROR", "code": "NO_PRODUCT", "detail": "No available product found on the store"}

        self._monorail()

        if not self.create_checkout_session():
            return {"category": "ERROR", "code": "CHECKOUT_FAILED", "detail": "Failed to create checkout session or extract tokens"}

        vault_id, addr = self.vault_card(cc_line)
        if not vault_id:
            return {"category": "ERROR", "code": "VAULT_FAILED", "detail": "Failed to vault card at payment processor"}

        cc_number = cc_line.split("|")[0].strip() if "|" in cc_line else ""
        receipt_id = self.submit(vault_id, addr, card_number=cc_number)
        if not receipt_id:
            reason = getattr(self, 'failure_reason', 'Payment submission rejected')
            return {"category": "DECLINED", "code": "SUBMISSION_REJECTED", "detail": f"Payment submission was rejected: {reason}"}

        result = self.poll_receipt(receipt_id)
        if not result:
            return {"category": "ERROR", "code": "UNKNOWN", "detail": "Unknown error during polling"}

        if result[0] == "CHARGED":
            return {"category": "CHARGED", "code": "SUCCESS", "detail": result[1]}
        elif result[0] == "DECLINED":
            return {"category": "DECLINED", "code": result[1], "detail": result[2]}
        else:
            return {"category": result[0], "code": result[1] if len(result) > 1 else "UNKNOWN", "detail": result[2] if len(result) > 2 else "Unknown"}
