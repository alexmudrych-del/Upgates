#!/usr/bin/env python3
"""
Překlad produktového JSON ze složky Source z angličtiny do ostatních jazyků.

Překládaná pole (pouze pokud hodnota není null):
  title, short_description, long_description, seo_title, seo_description, seo_url

Pravidla jazyků:
  sk = cs   (slovenština dostane obsah z češtiny)
  no = en   (norština zůstane anglicky)
  ta = en   (tamilština zůstane anglicky)

Použití: python translate_product_descriptions.py [soubor.json]
         Bez argumentu: Source/PS901.json -> Target/PS901_translated.json
"""
import json
import os
import sys
import time

# Pole k překladu (hodnoty null se přeskakují)
TRANSLATE_KEYS = (
    "title",
    "short_description",
    "long_description",
    "seo_title",
    "seo_description",
    "seo_url",
)

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
    print()

    out_descriptions = []
    for desc in descriptions:
        lang = desc.get("language") or "en"
        out = dict(desc)
        target = get_translator_target(lang)

        if lang == source_lang:
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

        # sk → použít obsah z češtiny (cs)
        if lang in USE_CS_FOR:
            cs_entry = next(
                (d for d in out_descriptions if d.get("language") == "cs"), None
            )
            if cs_entry:
                for key in TRANSLATE_KEYS:
                    if cs_entry.get(key) is not None:
                        out[key] = cs_entry[key]
                print(f"  [{lang}] = cs (zkopírováno)")
            else:
                # cs ještě nebyl v pořadí – přeložíme en→cs a použijeme pro sk
                trans = GoogleTranslator(source=source_lang, target="cs")
                for key in TRANSLATE_KEYS:
                    val = source_desc.get(key)
                    if val is not None and str(val).strip():
                        out[key] = translate_text(trans, val)
                        time.sleep(0.2)
                print(f"  [{lang}] = cs (přeloženo en→cs)")
            out_descriptions.append(out)
            continue

        # Ostatní jazyky – překlad z en
        trans = GoogleTranslator(source=source_lang, target=target)
        for key in TRANSLATE_KEYS:
            val = source_desc.get(key)
            if val is not None and str(val).strip():
                out[key] = translate_text(trans, val)
                print(f"  [{lang}] {key} OK")
                time.sleep(0.2)
        out_descriptions.append(out)

    data["descriptions"] = out_descriptions
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nHotovo. Uloženo: {output_path}")


if __name__ == "__main__":
    main()
