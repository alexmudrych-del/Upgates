#!/usr/bin/env python3
"""
Překlad produktového JSON ze složky Source z angličtiny do ostatních jazyků.

Překládaná pole (pouze pokud hodnota není null):
  title, short_description, long_description, seo_title, seo_description, seo_url

Pravidla jazyků:
  sk = cs   (slovenština dostane obsah z češtiny)
  no = en   (norština zůstane anglicky)
  ta = en   (tamilština zůstane anglicky)
  
DŮLEŽITÉ:
  - Pokud v překladech již existuje český překlad, ponechat ho beze změny
  - Pokud v překladech již existuje slovenský překlad, ponechat ho beze změny

Použití: python translate_product_descriptions.py [soubor.json]
         Bez argumentu: Source/PS901.json -> Target/PS901_translated.json
"""
import json
import os
import re
import sys
import time

# Značka PilotStyle se nikdy nemění – chybné varianty od překladače
BRAND_WRONG_VARIANTS = ("PilótaStyle", "PiloteStyle", "PilotaStyle", "ПилотStyle", "PilotsStyle", "Pilot Styl")
BRAND_CORRECT = "PilotStyle"

try:
    from use_aviation_database import replace_aviation_terms
    _has_aviation_db = True
except ImportError:
    _has_aviation_db = False

# Pole k překladu v descriptions (hodnoty null se přeskakují)
TRANSLATE_KEYS = (
    "title",
    "short_description",
    "long_description",
    "seo_title",
    "seo_description",
    "seo_url",
)

# Meta pole k překladu (odpovídá AAA_popis1_obrazek, AAA_popis1_text, atd. v e-shopu)
META_KEYS_TO_TRANSLATE = (
    "row1_img",           # AAA_popis1_obrazek
    "row1_text",          # AAA_popis1_text
    "row2_img",           # AAA_popis2_obrazek
    "row2_text",          # AAA_popis2_text
    "custom_key_2",       # AAA_popis_horni_obrazek / horni_text
    "custom_key_3",
    "custom_key_4",       # AAA_popis_mezi_bloky_text
    "vlastnosti",         # AAA_popis_vlastnosti
    "seo_text",
    # Přímo názvy z e-shopu, pokud se v JSON vyskytnou:
    "AAA_popis1_obrazek",
    "AAA_popis1_text",
    "AAA_popis2_obrazek",
    "AAA_popis2_text",
    "AAA_popis_horni_obrazek",
    "AAA_popis_horni_text",
    "AAA_popis_mezi_bloky_text",
    "AAA_popis_vlastnosti",
)


def _should_translate_meta_key(key):
    """True pokud má být meta pole překládáno."""
    if key in META_KEYS_TO_TRANSLATE:
        return True
    if key and key.startswith("AAA_popis"):
        return True
    return False

# Mapování jazykových kódů pro překladač (pokud se liší od pole language)
LANG_MAP = {}

# Pravidla: sk používá obsah cs; no a ta zůstávají v angličtině
USE_CS_FOR = ["sk"]
USE_EN_FOR = ["no", "ta"]

CHUNK_SIZE = 4500

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(SCRIPT_DIR, "Source")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "Target")
DEFAULT_INPUT = "PS901.json"


def get_translator_target(lang):
    return LANG_MAP.get(lang, lang)


def apply_aviation_terms(text, target_lang):
    """Pokud je k dispozici letecká databáze, nahradí známé termíny dle pravidel."""
    if not _has_aviation_db or not text or not str(text).strip():
        return text
    return replace_aviation_terms(str(text), source_lang="en", target_lang=target_lang)


def fix_brand_pilotstyle(text):
    """Vrátí text s opravenou značkou PilotStyle (nikdy neměnit)."""
    if not text or not isinstance(text, str):
        return text
    result = text
    for wrong in BRAND_WRONG_VARIANTS:
        result = result.replace(wrong, BRAND_CORRECT)
    return result


def fix_hu_leading_article(text):
    """U maďarštiny odstraní úvodní člen A / Az na začátku textu."""
    if not text or not isinstance(text, str):
        return text
    return re.sub(r"^\s*(?:Az\s+|A\s+)", "", text, count=1)


def postprocess_translation(text, lang):
    """Opravy po překladu: značka PilotStyle neměnná, u HU odstranit úvodní A/Az."""
    text = fix_brand_pilotstyle(text)
    if lang == "hu":
        text = fix_hu_leading_article(text)
    return text


def _meta_lang_to_target(meta_lang_key):
    """Mapuje klíč jazyka v metas (cz, sk, …) na cílový jazyk pro překlad."""
    if meta_lang_key == "en":
        return None
    if meta_lang_key in ("cz", "cs"):
        return "cs"
    if meta_lang_key == "sk":
        return "sk"
    if meta_lang_key in USE_EN_FOR:
        return "en"
    return meta_lang_key


def _translate_metas(metas, source_lang, GoogleTranslator):
    """Přeloží hodnoty v data['metas'] u vybraných klíčů (row1_text, vlastnosti, …)."""
    # Pořadí: nejdřív cz/cs (aby sk mohl kopírovat), pak sk, no/ta, ostatní
    order = ("cz", "cs", "sk", "no", "ta", "fr", "it", "de", "pl", "hu", "ru")
    for meta in metas:
        key = meta.get("key")
        if not _should_translate_meta_key(key):
            continue
        values = meta.get("values") or {}
        en_entry = values.get("en")
        if isinstance(en_entry, dict):
            en_val = en_entry.get("value")
        else:
            en_val = None
        if not en_val or not str(en_val).strip():
            continue
        done = set()
        for meta_lang_key in order:
            if meta_lang_key not in values or meta_lang_key in done:
                continue
            done.add(meta_lang_key)
            target_lang = _meta_lang_to_target(meta_lang_key)
            if target_lang is None:
                continue
            entry = values[meta_lang_key]
            if not isinstance(entry, dict):
                continue
            existing = entry.get("value")
            if target_lang == "cs":
                # V metas vždy přeložit z en (aby se doplnily i pole, kde cz měl jen kopii en)
                trans = GoogleTranslator(source=source_lang, target="cs")
                new_val = translate_text(trans, en_val)
                new_val = apply_aviation_terms(new_val, "cs")
                new_val = postprocess_translation(new_val, "cs")
                entry["value"] = new_val
                print(f"    meta {key} [{meta_lang_key}] OK")
                time.sleep(0.2)
            elif target_lang == "sk":
                cz_entry = values.get("cz") or values.get("cs")
                cz_val = cz_entry.get("value") if isinstance(cz_entry, dict) else None
                if cz_val is not None:
                    entry["value"] = cz_val
                    print(f"    meta {key} [sk] = cs")
            elif target_lang == "en":
                entry["value"] = en_val
                print(f"    meta {key} [{meta_lang_key}] = en")
            else:
                # Vždy přeložit z en – nepřeskakovat kvůli drobným rozdílům v HTML (existing vs en_val)
                trans = GoogleTranslator(source=source_lang, target=get_translator_target(target_lang))
                new_val = translate_text(trans, en_val)
                new_val = apply_aviation_terms(new_val, target_lang)
                new_val = postprocess_translation(new_val, target_lang)
                entry["value"] = new_val
                print(f"    meta {key} [{meta_lang_key}] OK")
                time.sleep(0.2)
        for meta_lang_key in values:
            if meta_lang_key in done or meta_lang_key == "en":
                continue
            done.add(meta_lang_key)
            target_lang = _meta_lang_to_target(meta_lang_key)
            if target_lang is None:
                continue
            entry = values[meta_lang_key]
            if not isinstance(entry, dict):
                continue
            existing = entry.get("value")
            if target_lang == "sk":
                cz_entry = values.get("cz") or values.get("cs")
                cz_val = cz_entry.get("value") if isinstance(cz_entry, dict) else None
                if cz_val is not None:
                    entry["value"] = cz_val
                    print(f"    meta {key} [{meta_lang_key}] = cs")
            elif target_lang == "en":
                entry["value"] = en_val
                print(f"    meta {key} [{meta_lang_key}] = en")
            else:
                trans = GoogleTranslator(source=source_lang, target=get_translator_target(target_lang))
                new_val = translate_text(trans, en_val)
                new_val = apply_aviation_terms(new_val, target_lang)
                new_val = postprocess_translation(new_val, target_lang)
                entry["value"] = new_val
                print(f"    meta {key} [{meta_lang_key}] OK")
                time.sleep(0.2)


def translate_text(translator, text):
    if text is None or not str(text).strip():
        return text
    text = str(text).strip()
    if len(text) <= CHUNK_SIZE:
        try:
            return translator.translate(text)
        except Exception as e:
            print(f"    Chyba překladu: {e}")
            return text
    parts = []
    rest = text
    while rest:
        if len(rest) <= CHUNK_SIZE:
            parts.append(rest)
            break
        chunk = rest[:CHUNK_SIZE]
        last_break = max(
            chunk.rfind("</p>"),
            chunk.rfind("<p "),
            chunk.rfind(". "),
            chunk.rfind(".\n"),
        )
        if last_break > CHUNK_SIZE // 2:
            chunk = rest[: last_break + 1]
            rest = rest[last_break + 1 :].lstrip()
        else:
            rest = rest[CHUNK_SIZE:]
            chunk = chunk + (rest[:1] if rest and rest[0] in " \n" else "")
            if rest and rest[0] in " \n":
                rest = rest[1:]
        parts.append(chunk)
    try:
        return "".join(translator.translate(p) for p in parts)
    except Exception as e:
        print(f"    Chyba překladu (chunked): {e}")
        return text


def main():
    from deep_translator import GoogleTranslator

    input_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    if os.path.isabs(input_name) or os.path.dirname(input_name):
        input_path = input_name
        output_path = os.path.join(
            OUTPUT_DIR,
            os.path.basename(input_name).replace(".json", "_translated.json"),
        )
    else:
        input_path = os.path.join(SOURCE_DIR, input_name)
        output_path = os.path.join(
            OUTPUT_DIR,
            input_name.replace(".json", "_translated.json"),
        )

    if not os.path.isfile(input_path):
        raise SystemExit(f"Soubor nenalezen: {input_path}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    descriptions = data.get("descriptions") or []
    if not descriptions:
        raise SystemExit("V datech chybí descriptions.")

    source_lang = "en"
    source_desc = next(
        (d for d in descriptions if d.get("language") == source_lang), descriptions[0]
    )
    target_languages = list({d.get("language") for d in descriptions if d.get("language")})

    print(f"Vstup: {input_path}")
    print(f"Výstup: {output_path}")
    print(f"Zdroj: {source_lang}, cílové jazyky: {target_languages}")
    print(f"Pravidla: {USE_CS_FOR} = cs, {USE_EN_FOR} = en (bez překladu)")
    print("Letecká databáze: zapnuta (konzistence termínů)" if _has_aviation_db else "Letecká databáze: není k dispozici")
    print()

    out_descriptions = []
    for desc in descriptions:
        lang = desc.get("language") or "en"
        out = dict(desc)
        target = get_translator_target(lang)

        if lang == source_lang:
            out_descriptions.append(out)
            continue

        # PRAVIDLO: U cs ponechat jen pole, která se skutečně liší od en (už přeložená); ostatní přeložit
        if lang == "cs":
            trans = GoogleTranslator(source=source_lang, target="cs")
            for key in TRANSLATE_KEYS:
                val = source_desc.get(key)
                if val is None or not str(val).strip():
                    continue
                existing_val = desc.get(key)
                # Ponechat existující překlad jen pokud je vyplněný a jiný než en
                if (
                    existing_val is not None
                    and str(existing_val).strip()
                    and existing_val != val
                ):
                    out[key] = existing_val
                    print(f"  [{lang}] {key} = ponecháno")
                else:
                    out[key] = translate_text(trans, val)
                    out[key] = apply_aviation_terms(out[key], "cs")
                    out[key] = postprocess_translation(out[key], lang)
                    print(f"  [{lang}] {key} OK")
                    time.sleep(0.2)
            out_descriptions.append(out)
            continue

        # PRAVIDLO: U sk ponechat jen pole skutečně přeložená (jiná než en); ostatní vzít z cs
        if lang == "sk":
            cs_entry = next(
                (d for d in out_descriptions if d.get("language") == "cs"), None
            )
            for key in TRANSLATE_KEYS:
                val = source_desc.get(key)
                if val is None or not str(val).strip():
                    continue
                existing_val = desc.get(key)
                if (
                    existing_val is not None
                    and str(existing_val).strip()
                    and existing_val != val
                ):
                    out[key] = existing_val
                    print(f"  [{lang}] {key} = ponecháno")
                elif cs_entry and cs_entry.get(key) is not None:
                    out[key] = cs_entry[key]
                    print(f"  [{lang}] {key} = cs")
                else:
                    trans = GoogleTranslator(source=source_lang, target="cs")
                    out[key] = translate_text(trans, val)
                    out[key] = apply_aviation_terms(out[key], "cs")
                    out[key] = postprocess_translation(out[key], lang)
                    print(f"  [{lang}] {key} OK")
                    time.sleep(0.2)
            out_descriptions.append(out)
            continue

        # no, ta → ponechat angličtinu
        if lang in USE_EN_FOR:
            for key in TRANSLATE_KEYS:
                if source_desc.get(key) is not None:
                    out[key] = source_desc[key]
            print(f"  [{lang}] = en (zkopírováno)")
            out_descriptions.append(out)
            continue

        # Ostatní jazyky – překlad z en
        trans = GoogleTranslator(source=source_lang, target=target)
        for key in TRANSLATE_KEYS:
            val = source_desc.get(key)
            if val is not None and str(val).strip():
                out[key] = translate_text(trans, val)
                out[key] = apply_aviation_terms(out[key], lang)
                out[key] = postprocess_translation(out[key], lang)
                print(f"  [{lang}] {key} OK")
                time.sleep(0.2)
        out_descriptions.append(out)

    data["descriptions"] = out_descriptions

    # Překlad meta polí (row1_text, row2_text, vlastnosti, seo_text, custom_key_*, …)
    metas = data.get("metas") or []
    if metas:
        print("Meta pole:")
        _translate_metas(metas, source_lang, GoogleTranslator)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nHotovo. Uloženo: {output_path}")


if __name__ == "__main__":
    main()
