#!/usr/bin/env python3
"""
Stáhne produkt PS600 z Upgates API a zobrazí všechna pole
(včetně short/long text a custom fields).
"""
import json
import os
import requests
from requests.auth import HTTPBasicAuth

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_PATH = os.path.join(SCRIPT_DIR, "upgates_credentials.json")

def load_credentials():
    with open(CREDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    creds = load_credentials()
    api_url = creds["api_url"].rstrip("/")
    auth = HTTPBasicAuth(creds["login"], creds["api_key"])
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # 1) Seznam produktů - hledáme PS600 (podle kódu nebo názvu)
    print("Načítám seznam produktů (bez parametrů)...")
    r = requests.get(
        f"{api_url}/products",
        auth=auth,
        headers=headers,
        timeout=30,
    )
    if not r.ok:
        print(f"Chyba {r.status_code}: {r.text[:500]}")
    r.raise_for_status()
    data = r.json()

    # Rozbalení podle možného formátu odpovědi
    products = data if isinstance(data, list) else data.get("data") or data.get("products") or []
    if not isinstance(products, list):
        products = [products]

    print(f"Celkem načteno produktů: {len(products)}")
    codes = [str(p.get("code") or p.get("product_code") or "").strip() for p in products[:30]]
    print(f"Ukázka kódů (prvních 30): {codes}")

    product_id = None
    product_from_list = None
    for p in products:
        code = p.get("code") or p.get("product_code") or p.get("sku") or ""
        if str(code).strip().upper() == "PS600":
            product_id = p.get("id") or p.get("product_id")
            print(f"Nalezen produkt PS600, id = {product_id}")
            break

    if not product_id:
        # Zkusíme endpoint s filtrem kód
        r3 = requests.get(
            f"{api_url}/products",
            auth=auth,
            headers=headers,
            params={"code": "PS600"},
            timeout=30,
        )
        if r3.ok:
            data3 = r3.json()
            plist = data3 if isinstance(data3, list) else data3.get("data") or data3.get("products") or []
            if plist:
                product_id = plist[0].get("id") or plist[0].get("product_id")
                product_from_list = plist[0]
                print(f"Nalezeno přes ?code=PS600, id = {product_id}")
        if not product_id:
            print("Produkt PS600 nenalezen. Prohlédneme strukturu prvního produktu.")
            if products:
                product_id = products[0].get("id") or products[0].get("product_id")
                print(f"Použit první produkt (id={product_id}) pro ukázku polí.")
            else:
                return

    # 2) Detail produktu (nebo použijeme produkt z odpovědi ?code=PS600)
    if product_from_list is not None:
        print("Používám data z odpovědi ?code=PS600 (bez dalšího volání).")
        product = product_from_list
    else:
        print(f"\nNačítám detail produktu id={product_id}...")
        r_detail = requests.get(
            f"{api_url}/products/{product_id}",
            auth=auth,
            headers=headers,
            timeout=30,
        )
        r_detail.raise_for_status()
        product = r_detail.json()
        if isinstance(product, dict) and "products" in product and product["products"]:
            product = product["products"][0]
        elif isinstance(product, dict) and "data" in product:
            product = product["data"]

    # 3) Výpis všech klíčů a vybraných polí
    def all_keys(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                key = f"{prefix}.{k}" if prefix else k
                yield key
                yield from all_keys(v, key)
        elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
            yield from all_keys(obj[0], f"{prefix}[0]")

    print("\n" + "=" * 60)
    print("VŠECHNA POLE (klíče) v odpovědi produktu:")
    print("=" * 60)
    for key in sorted(set(all_keys(product))):
        print(f"  {key}")

    # Hledaná pole – API má descriptions[].short_description, descriptions[].long_description a metas[] (key + values)
    short_text = product.get("short_description") or product.get("short_text")
    long_text = product.get("description") or product.get("long_description") or product.get("long_text")
    descr = product.get("descriptions")
    if isinstance(descr, list) and descr:
        d = descr[0]
        short_text = short_text or d.get("short_description") or d.get("short") or d.get("title")
        long_text = long_text or d.get("long_description") or d.get("long") or d.get("description") or d.get("content")
    custom = product.get("custom_fields") or product.get("custom") or product.get("customFields")
    metas = product.get("metas")  # list of {key, type, values: {cz: {value}, en: {value}, ...}}

    print("\n" + "=" * 60)
    print("HLEDANÁ POLE:")
    print("=" * 60)
    print("\n--- Short text (prvních 200 znaků) ---")
    print((short_text or "(nenalezeno)")[:200] if short_text else "(nenalezeno)")
    print("\n--- Long text (prvních 300 znaků) ---")
    print((long_text or "(nenalezeno)")[:300] if long_text else "(nenalezeno)")
    print("\n--- Custom fields (metas) ---")
    if isinstance(metas, list):
        for m in metas:
            key = m.get("key") or m.get("name") or "?"
            vals = m.get("values") or {}
            # hodnota: první dostupný jazyk (cz, en, ...)
            val = None
            for lang in ("cz", "cs", "en", "sk"):
                if isinstance(vals.get(lang), dict):
                    val = (vals.get(lang) or {}).get("value")
                elif vals.get(lang) is not None:
                    val = vals.get(lang)
                if val:
                    break
            if val is None and vals:
                val = list(vals.values())[0] if vals else None
            val_str = (str(val)[:200] + "...") if val and len(str(val)) > 200 else (val or "(prázdné)")
            print(f"  {key}: {val_str}")
    elif custom and isinstance(custom, dict):
        for k, v in custom.items():
            print(f"  {k}: {str(v)[:150]}")
    else:
        print("  (žádné metas nebo jiný formát)")

    # Hledaná custom pole AAA_*
    aaa_wanted = ["AAA_popis1_obrazek", "AAA_popis1_text", "AAA_popis2_obrazek", "AAA_popis_horni_text", "AAA_popis_mezi_bloky_text"]
    if isinstance(metas, list):
        wanted_upper = [k.upper() for k in aaa_wanted]
        aaa_found = [m for m in metas if (m.get("key") or "").upper() in wanted_upper]
        print("\n--- Požadovaná pole AAA_* ---")
        for m in aaa_found:
            key = m.get("key")
            vals = m.get("values") or {}
            v = (vals.get("cz") or {}).get("value") if isinstance(vals.get("cz"), dict) else (vals.get("cz") or (list(vals.values())[0] if vals else None))
            print(f"  {key}: {(str(v)[:150] + '...') if v and len(str(v)) > 150 else (v or '(prázdné)')}")
        if not aaa_found:
            print("  Žádné z těchto klíčů v metas nenalezeno.")

    print("\n" + "=" * 60)
    print("CELÝ JSON odpovědi (pro kontrolu):")
    print("=" * 60)
    print(json.dumps(product, ensure_ascii=False, indent=2)[:8000])
    if len(json.dumps(product)) > 8000:
        print("\n... (zkráceno)")

if __name__ == "__main__":
    main()
