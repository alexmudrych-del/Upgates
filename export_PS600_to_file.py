#!/usr/bin/env python3
"""
Stáhne produkt PS600 z Upgates API a zapíše výstup do TEST PS600.txt a TEST PS600.json
"""
import json
import os
import requests
from requests.auth import HTTPBasicAuth

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_PATH = os.path.join(SCRIPT_DIR, "upgates_credentials.json")
OUTPUT_TXT = os.path.join(SCRIPT_DIR, "TEST PS600.txt")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "TEST PS600.json")

def load_credentials():
    with open(CREDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_meta_value(m, lang_first=("cz", "cs", "en", "sk", "de")):
    vals = m.get("values") or {}
    for lang in lang_first:
        v = vals.get(lang)
        if isinstance(v, dict):
            v = v.get("value")
        if v is not None and str(v).strip():
            return v
    if vals:
        first = next(iter(vals.values()))
        return first.get("value") if isinstance(first, dict) else first
    return None

def main():
    creds = load_credentials()
    api_url = creds["api_url"].rstrip("/")
    auth = HTTPBasicAuth(creds["login"], creds["api_key"])
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    r = requests.get(
        f"{api_url}/products",
        auth=auth,
        headers=headers,
        params={"code": "PS600"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    plist = data if isinstance(data, list) else data.get("data") or data.get("products") or []
    if not plist:
        raise SystemExit("Produkt PS600 nenalezen.")
    product = plist[0]

    lines = []
    lines.append("=" * 80)
    lines.append("PRODUKT PS600 – VŠECHNY HODNOTY / OBSAH (Upgates API)")
    lines.append("=" * 80)
    lines.append("")

    # Základní údaje
    lines.append("--- ZÁKLADNÍ ÚDAJE ---")
    lines.append(f"code: {product.get('code')}")
    lines.append(f"product_id: {product.get('product_id')}")
    lines.append(f"active_yn: {product.get('active_yn')}")
    lines.append(f"archived_yn: {product.get('archived_yn')}")
    lines.append(f"ean: {product.get('ean')}")
    lines.append(f"manufacturer: {product.get('manufacturer')}")
    lines.append(f"availability: {product.get('availability')}")
    lines.append(f"stock: {product.get('stock')}")
    lines.append(f"admin_url: {product.get('admin_url')}")
    lines.append("")

    # Popisy (descriptions) – všechny jazyky
    lines.append("--- DESCRIPTIONS (popisy po jazycích) ---")
    for d in product.get("descriptions") or []:
        lang = d.get("language", "?")
        lines.append(f"\n  [Jazyk: {lang}]")
        lines.append(f"  title: {d.get('title') or ''}")
        lines.append(f"  short_description: {d.get('short_description') or '(prázdné)'}")
        long_desc = d.get("long_description") or ""
        lines.append(f"  long_description:\n{long_desc}")
        lines.append(f"  url: {d.get('url') or ''}")
        lines.append(f"  seo_title: {d.get('seo_title') or ''}")
        lines.append(f"  seo_description: {d.get('seo_description') or ''}")
        lines.append(f"  seo_url: {d.get('seo_url') or ''}")
        lines.append(f"  unit: {d.get('unit') or ''}")
    lines.append("")

    # Short text / Long text (souhrn – první jazyk)
    descr = product.get("descriptions") or []
    if descr:
        d0 = descr[0]
        short = d0.get("short_description") or d0.get("title") or ""
        long_ = d0.get("long_description") or ""
        lines.append("--- SHORT TEXT (souhrn) ---")
        lines.append(short)
        lines.append("")
        lines.append("--- LONG TEXT (souhrn) ---")
        lines.append(long_)
        lines.append("")

    # Custom pole (metas) – všechna
    lines.append("--- CUSTOM FIELDS (metas) – všechny klíče a hodnoty ---")
    for m in product.get("metas") or []:
        key = m.get("key") or m.get("name") or "?"
        val = get_meta_value(m)
        val_str = (val if val is not None else "(prázdné)")
        lines.append(f"\n  [{key}]")
        lines.append(str(val_str))
    lines.append("")

    # Obrázky
    lines.append("--- IMAGES ---")
    for i, img in enumerate(product.get("images") or []):
        lines.append(f"  [{i}] url: {img.get('url')}")
        lines.append(f"       main_yn: {img.get('main_yn')}, position: {img.get('position')}")
    lines.append("")

    # Ceny (stručně)
    lines.append("--- PRICES (stručně) ---")
    for pr in product.get("prices") or []:
        lines.append(f"  currency: {pr.get('currency')}, language: {pr.get('language')}")
        for pl in pr.get("pricelists") or []:
            lines.append(f"    - {pl.get('name')}: price_with_vat={pl.get('price_with_vat')}, price_without_vat={pl.get('price_without_vat')}")
    lines.append("")

    # Kategorie
    lines.append("--- CATEGORIES ---")
    for c in product.get("categories") or []:
        lines.append(f"  - {c.get('name')} (code: {c.get('code')}, main_yn: {c.get('main_yn')})")
    lines.append("")

    # Celý JSON (pro úplnost)
    lines.append("--- CELÝ JSON ODPOVĚDI (raw) ---")
    lines.append(json.dumps(product, ensure_ascii=False, indent=2))

    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(product, f, ensure_ascii=False, indent=2)

    print(f"Hotovo. Textový výstup: {OUTPUT_TXT}")
    print(f"JSON výstup: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
