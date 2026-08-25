#!/usr/bin/env python3
"""Reads data.json (Meta Ads + Shopify) and regenerates the auto-derivable
tables under data/. Does NOT touch index.html / internas.html / recomendaciones.html
(those carry curated narrative) — see README for what's manual vs automatic.
"""
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

PURCHASE_ACTIONS = {"purchase", "omni_purchase"}


def num(x):
    return float(x) if x not in (None, "") else 0.0


def action_value(actions, wanted):
    for a in actions or []:
        if a.get("action_type") in wanted:
            return num(a["value"])
    return 0.0


def month_key(d):
    return d[:7]  # "YYYY-MM"


def load():
    return json.loads(Path("data.json").read_text())


def build_meta_monthly(data):
    by_month = defaultdict(lambda: defaultdict(float))
    for row in data["meta_daily"]:
        mk = month_key(row["date_start"])
        by_month[mk]["spend"] += num(row.get("spend"))
        by_month[mk]["clicks"] += num(row.get("clicks"))
        by_month[mk]["impressions"] += num(row.get("impressions"))
        by_month[mk]["frequency_sum"] += num(row.get("frequency"))
        by_month[mk]["days"] += 1

    lines = ["# Evolución mensual · Meta Ads (auto-generado)\n", f"_Actualizado: {date.today().isoformat()}_\n"]
    lines.append(
        "**⚠️ El pixel de Meta no tiene ningún evento de `purchase` configurado "
        "(0 en los 3 años de historial de la cuenta) — no hay Ventas/ROAS/CPA nativos de Meta que reportar.** "
        "El ROAS de los reportes anteriores salía de cruzar manualmente el total de Shopify contra el gasto del mes, "
        "no de atribución real de Meta. Vale la pena revisar si el Conversions API / pixel está bien instalado en el checkout.\n"
    )
    lines.append("| Mes | Inversión | Clics | CPC | Frecuencia |")
    lines.append("|---|---:|---:|---:|---:|")
    for mk in sorted(by_month):
        m = by_month[mk]
        cpc = m["spend"] / m["clicks"] if m["clicks"] else 0
        freq = m["frequency_sum"] / m["days"] if m["days"] else 0
        lines.append(f"| {mk} | ${m['spend']:,.0f} | {m['clicks']:.0f} | ${cpc:.2f} | {freq:.1f} |")
    Path("data/01-meta-mensual.md").write_text("\n".join(lines) + "\n")
    print("✓ data/01-meta-mensual.md")


def build_meta_campaigns(data):
    rows = []
    for c in data["meta_campaign_insights"]:
        spend = num(c.get("spend"))
        rows.append((c.get("campaign_name", "—"), spend, num(c.get("clicks")), num(c.get("ctr")), num(c.get("frequency"))))
    rows.sort(key=lambda r: -r[1])

    lines = ["# Top campañas · histórico (auto-generado)\n", f"_Actualizado: {date.today().isoformat()}_\n"]
    lines.append("_Sin eventos de `purchase` en el pixel — no hay Ventas/ROAS/Compras por campaña que reportar (ver 01-meta-mensual.md)._\n")
    lines.append("| # | Campaña | Inversión | Clics | CTR | Frecuencia |")
    lines.append("|---|---|---:|---:|---:|---:|")
    for i, (name, spend, clicks, ctr, freq) in enumerate(rows, 1):
        lines.append(f"| {i} | {name} | ${spend:,.0f} | {clicks:.0f} | {ctr:.2f}% | {freq:.1f} |")
    Path("data/02-meta-campañas.md").write_text("\n".join(lines) + "\n")
    print("✓ data/02-meta-campañas.md")


# Fixed MX retail calendar. Add new ranges here as they happen; performance is
# recomputed from meta_daily every run, so past events never go stale.
KEY_DATES = [
    ("Día del Padre 2025", "2025-06-09", "2025-06-15"),
    ("Halloween 2025", "2025-10-25", "2025-10-31"),
    ("Buen Fin 2025", "2025-11-14", "2025-11-17"),
    ("Black Friday 2025", "2025-11-27", "2025-11-29"),
    ("Navidad 2025", "2025-12-20", "2025-12-25"),
    ("Día del Niño 2026", "2026-04-27", "2026-05-03"),
    ("Día del Padre 2026", "2026-06-08", "2026-06-14"),
    ("Regreso a clases 2026", "2026-08-01", "2026-08-23"),
]


def build_key_dates(data):
    daily_by_date = {row["date_start"]: row for row in data["meta_daily"]}
    lines = ["# Performance en fechas clave (auto-generado)\n", f"_Actualizado: {date.today().isoformat()}_\n"]
    lines.append("_Ventas y ROAS son atribución de Meta (7d clic / 1d vista), no pedidos de Shopify._\n")
    lines.append("| Fecha | Rango | Inversión | Clics | CTR prom. | Ventas | Revenue | ROAS |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for name, start, end in KEY_DATES:
        spend = clicks = impressions = purch = rev = 0.0
        days = 0
        for ds, row in daily_by_date.items():
            if start <= ds <= end:
                spend += num(row.get("spend"))
                clicks += num(row.get("clicks"))
                impressions += num(row.get("impressions"))
                purch += action_value(row.get("actions"), PURCHASE_ACTIONS)
                rev += action_value(row.get("action_values"), PURCHASE_ACTIONS)
                days += 1
        ctr = clicks / impressions * 100 if impressions else 0
        roas = rev / spend if spend else 0
        lines.append(f"| {name} | {start} → {end} ({days}d) | ${spend:,.0f} | {clicks:.0f} | {ctr:.2f}% | {purch:.0f} | ${rev:,.0f} | {roas:.2f}x |")
    Path("data/03-meta-fechas-clave.md").write_text("\n".join(lines) + "\n")
    print("✓ data/03-meta-fechas-clave.md")


def build_products(data):
    orders = data["shopify_orders"]
    agg = defaultdict(lambda: {"revenue": 0.0, "units": 0, "orders": set()})
    for o in orders:
        for li in o.get("line_items", []):
            key = li.get("title", "—")
            agg[key]["revenue"] += num(li.get("price")) * num(li.get("quantity"))
            agg[key]["units"] += int(li.get("quantity") or 0)
            agg[key]["orders"].add(o["id"])
    rows = sorted(agg.items(), key=lambda kv: -kv[1]["revenue"])

    lines = [
        "# Top productos · Shopify (auto-generado, ventana disponible vía API)\n",
        f"_Actualizado: {date.today().isoformat()} · {len(orders)} órdenes en la ventana accesible por el token_\n",
    ]
    lines.append("| # | Producto | Revenue | Unidades | Órdenes |")
    lines.append("|---|---|---:|---:|---:|")
    for i, (name, v) in enumerate(rows[:20], 1):
        lines.append(f"| {i} | {name} | ${v['revenue']:,.0f} | {v['units']} | {len(v['orders'])} |")
    Path("data/05-shopify-productos.md").write_text("\n".join(lines) + "\n")
    print("✓ data/05-shopify-productos.md")


def build_geo(data):
    orders = data["shopify_orders"]
    counts = defaultdict(int)
    total = 0
    for o in orders:
        addr = o.get("shipping_address") or o.get("billing_address")
        if not addr:
            continue
        counts[addr.get("province") or "—"] += 1
        total += 1

    lines = [
        "# Distribución geográfica · Shopify (auto-generado)\n",
        f"_Actualizado: {date.today().isoformat()} · {total} órdenes con dirección_\n",
    ]
    lines.append("| # | Estado | Órdenes | % del total |")
    lines.append("|---|---|---:|---:|")
    for i, (state, n) in enumerate(sorted(counts.items(), key=lambda kv: -kv[1]), 1):
        pct = n / total * 100 if total else 0
        lines.append(f"| {i} | {state} | {n} | {pct:.1f}% |")
    Path("data/06-shopify-geo.md").write_text("\n".join(lines) + "\n")
    print("✓ data/06-shopify-geo.md")


def build_promos(data):
    orders = data["shopify_orders"]
    counts = defaultdict(int)
    total = 0
    for o in orders:
        codes = o.get("discount_codes") or []
        if codes:
            total += 1
        for dc in codes:
            counts[dc.get("code", "—")] += 1

    lines = [
        "# Códigos de descuento usados · Shopify (auto-generado)\n",
        f"_Actualizado: {date.today().isoformat()} · {len(orders)} órdenes en la ventana accesible_\n",
    ]
    lines.append("| Código | Usos | % de órdenes |")
    lines.append("|---|---:|---:|")
    for code, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = n / len(orders) * 100 if orders else 0
        lines.append(f"| `{code}` | {n} | {pct:.1f}% |")
    Path("data/07-shopify-promos.md").write_text("\n".join(lines) + "\n")
    print("✓ data/07-shopify-promos.md")


def build_customers(data):
    customers = [c for c in data["shopify_customers"] if num(c.get("total_spent")) > 0]
    customers.sort(key=lambda c: -num(c.get("total_spent")))
    total_ltv = sum(num(c.get("total_spent")) for c in customers)
    repeaters = [c for c in customers if int(c.get("orders_count") or 0) >= 2]

    lines = ["# Clientes · Shopify (auto-generado)\n", f"_Actualizado: {date.today().isoformat()} · {len(customers)} clientes con compras_\n"]
    lines.append("## Stats generales\n")
    lines.append(f"- **Customers con compras:** {len(customers)}")
    lines.append(f"- **LTV total:** ${total_ltv:,.0f}")
    lines.append(f"- **LTV promedio:** ${(total_ltv / len(customers)) if customers else 0:,.0f}")
    if customers:
        lines.append(f"- **Clientes que repiten (2+ órdenes):** {len(repeaters)} ({len(repeaters)/len(customers)*100:.1f}%)")
    lines.append("\n## Top 10 LTV\n")
    lines.append("| # | Cliente | LTV | Órdenes | Email |")
    lines.append("|---|---|---:|---:|---|")
    for i, c in enumerate(customers[:10], 1):
        name = f"{c.get('first_name') or ''} {c.get('last_name') or ''}".strip() or "—"
        lines.append(f"| {i} | {name} | ${num(c.get('total_spent')):,.0f} | {c.get('orders_count', 0)} | {c.get('email', '—')} |")
    Path("data/08-shopify-clientes.md").write_text("\n".join(lines) + "\n")
    print("✓ data/08-shopify-clientes.md")


SECTIONS = [
    ("01-meta-mensual.md",      "📅 Evolución mensual · Meta Ads"),
    ("02-meta-campañas.md",     "🎯 Top campañas · histórico"),
    ("03-meta-fechas-clave.md", "⚡ Performance en fechas clave"),
    ("04-shopify-atribucion.md","🛒 Atribución · Shopify vs Meta"),
    ("05-shopify-productos.md", "📦 Top productos · Shopify"),
    ("06-shopify-geo.md",       "🗺️ Distribución geográfica"),
    ("07-shopify-promos.md",    "🏷️ Códigos de descuento"),
    ("08-shopify-clientes.md",  "👥 Clientes y LTV"),
    ("09-presupuesto.md",       "💰 Propuesta de presupuesto · 12 meses"),
]


def build_consolidated():
    """Concatena data/01..09 en 00-todo-junto.md para copiar y pegar."""
    today = date.today().strftime("%d/%m/%Y")
    out = [
        "# Saber Legacy · Todos los datos",
        f"_Actualizado: {today}_\n",
        "Documento único con todas las tablas. Selecciona la sección, copia, "
        "pega en Notion / Excel / Google Sheets.\n",
        "## Índice\n",
    ]
    out += [f"{i}. {title}" for i, (_, title) in enumerate(SECTIONS, 1)]
    out.append("\n---")
    for fname, title in SECTIONS:
        src = Path("data") / fname
        if not src.exists():
            continue
        body = src.read_text().splitlines()
        # se descarta el H1 propio del archivo; el título de sección lo reemplaza
        body = [ln for ln in body if not ln.startswith("# ")]
        # los H2 internos bajan un nivel para no competir con el título de sección
        body = [("#" + ln) if ln.startswith("## ") else ln for ln in body]
        out.append(f"\n## {title}\n")
        out.append("\n".join(body).strip())
        out.append("\n---")
    Path("data/00-todo-junto.md").write_text("\n".join(out).rstrip() + "\n")
    print("✓ data/00-todo-junto.md")


def main():
    data = load()
    Path("data").mkdir(exist_ok=True)
    build_meta_monthly(data)
    build_meta_campaigns(data)
    build_key_dates(data)
    build_products(data)
    build_geo(data)
    build_promos(data)
    build_customers(data)
    build_consolidated()
    print(
        "\nNota: 04-shopify-atribucion.md (histórico completo Shopify vs Meta) y "
        "09-presupuesto.md (propuesta forward-looking) NO se regeneran — ver README."
    )


if __name__ == "__main__":
    main()
