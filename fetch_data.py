#!/usr/bin/env python3
"""Pulls Meta Ads + Shopify data for the Saber Legacy dashboard and writes data.json."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

META_API_VERSION = "v23.0"
META_BASE = f"https://graph.facebook.com/{META_API_VERSION}"
SHOPIFY_API_VERSION = "2024-10"

INSIGHT_FIELDS = (
    "spend,impressions,reach,clicks,ctr,cpc,cpm,frequency,actions,"
    "action_values,cost_per_action_type"
)


def load_env():
    env = {}
    for line in Path(".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


# ---------- Meta ----------

def meta_fetch(path, params, token):
    params = {**params, "access_token": token}
    url = f"{META_BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as resp:
        return json.loads(resp.read().decode())


def meta_paginate(path, params, token, max_pages=40):
    out = []
    page = meta_fetch(path, params, token)
    out.extend(page.get("data", []))
    pages = 1
    while pages < max_pages:
        nxt = page.get("paging", {}).get("next")
        if not nxt:
            break
        with urllib.request.urlopen(urllib.request.Request(nxt), timeout=60) as resp:
            page = json.loads(resp.read().decode())
        out.extend(page.get("data", []))
        pages += 1
    return out


def fetch_meta(env, data):
    token = env["ACCESS_TOKEN"]
    act = env["AD_ACCOUNT_ID"]

    print("→ meta: account info")
    data["meta_account"] = meta_fetch(
        act, {"fields": "name,account_status,currency,timezone_name,amount_spent,business_name"}, token
    )

    print("→ meta: daily insights (full history)")
    data["meta_daily"] = meta_paginate(
        f"{act}/insights",
        {"fields": INSIGHT_FIELDS, "date_preset": "maximum", "time_increment": 1, "limit": 200},
        token,
    )

    print("→ meta: campaigns")
    data["meta_campaigns"] = meta_paginate(
        f"{act}/campaigns",
        {"fields": "id,name,status,effective_status,objective,start_time,stop_time", "limit": 200},
        token,
    )

    print("→ meta: campaign insights (lifetime per campaign)")
    data["meta_campaign_insights"] = meta_paginate(
        f"{act}/insights",
        {"fields": f"campaign_id,campaign_name,{INSIGHT_FIELDS}", "level": "campaign", "date_preset": "maximum", "limit": 200},
        token,
    )


# ---------- Shopify ----------

def shopify_fetch(env, path, params=None):
    store = env["SHOPIFY_STORE"]
    token = env["SHOPIFY_TOKEN"]
    url = f"https://{store}.myshopify.com/admin/api/{SHOPIFY_API_VERSION}/{path}"
    if params:
        url += f"?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode())
        link = resp.headers.get("Link", "")
    next_url = None
    if link:
        for part in link.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
    return body, next_url


def shopify_paginate(env, path, params, key, max_pages=100):
    out = []
    body, next_url = shopify_fetch(env, path, params)
    out.extend(body.get(key, []))
    pages = 1
    while next_url and pages < max_pages:
        req = urllib.request.Request(next_url, headers={"X-Shopify-Access-Token": env["SHOPIFY_TOKEN"]})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode())
            link = resp.headers.get("Link", "")
        out.extend(body.get(key, []))
        next_url = None
        if link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
        pages += 1
    return out


def fetch_shopify(env, data):
    print("→ shopify: shop info")
    data["shopify_shop"], _ = shopify_fetch(env, "shop.json")

    print("→ shopify: orders (last 12 months, any status)")
    data["shopify_orders"] = shopify_paginate(
        env,
        "orders.json",
        {"status": "any", "limit": 250, "created_at_min": "2024-06-01T00:00:00-06:00"},
        "orders",
    )

    print("→ shopify: products")
    data["shopify_products"] = shopify_paginate(env, "products.json", {"limit": 250}, "products")

    print("→ shopify: customers")
    data["shopify_customers"] = shopify_paginate(env, "customers.json", {"limit": 250}, "customers")

    print("→ shopify: price rules / discounts")
    try:
        price_rules = shopify_paginate(env, "price_rules.json", {"limit": 250}, "price_rules")
        discount_codes = []
        for pr in price_rules:
            codes, _ = shopify_fetch(env, f"price_rules/{pr['id']}/discount_codes.json")
            discount_codes.extend(codes.get("discount_codes", []))
        data["shopify_price_rules"] = price_rules
        data["shopify_discount_codes"] = discount_codes
    except Exception as e:
        print(f"  ! price rules/discounts failed (token scope?): {e}")
        data["shopify_price_rules"] = []
        data["shopify_discount_codes"] = []


def main():
    env = load_env()
    data = {}
    fetch_meta(env, data)
    fetch_shopify(env, data)

    out = Path("data.json")
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n✓ wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
