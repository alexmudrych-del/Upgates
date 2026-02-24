#!/usr/bin/env python3
"""
Načte TEST PS600.json, přeloží title, long_description, seo_url (a seo_title, seo_description pokud nejsou null)
z jazyka zdroje do každého jazyka dle pole language. Výstup: Translated TEST PS600.json
"""
import json
import os
import time

# Mapování kódů jazyka na kódy Google Translate (pouze pokud se liší)
LANG_MAP = {}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_JSON = os.path.join(SCRIPT_DIR, "TEST PS600.json")
OUTPUT_JSON = os.path.join(SCRIPT_DIR, "Translated TEST PS600.json")

# Limit znaků na jeden požadavek (Google cca 5000)
CHUNK_SIZE = 4500


def get_translator_target(lang):
    return LANG_MAP.get(lang, lang)


def translate_text(translator, text):
    if not text or not str(text).strip():
        return text
    text = str(text).strip()
    if len(text) <= CHUNK_SIZE:
        try:
            return translator.translate(text)
        except Exception as e:
            print(f"    Chyba překladu: {e}")
            return text
    # Dělení na části (podle odstavců nebo CHUNK_SIZE)
    parts = []
    rest = text
    while rest:
        if len(rest) <= CHUNK_SIZE:
            parts.append(rest)
            break
        chunk = rest[:CHUNK_SIZE]
        last_break = max(chunk.rfind("</p>"), chunk.rfind("<p "), chunk.rfind(". "), chunk.rfind(".\n"))
        if last_break > CHUNK_SIZE // 2:
            chunk = rest[: last_break + 1]
            rest = rest[last_break + 1 :].lstrip()
        else:
            rest = rest[CHUNK_SIZE:]
            chunk = chunk + rest[:1] if rest and rest[0] in " \n" else chunk
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

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    descriptions = data.get("descriptions") or []
    if not descriptions:
        raise SystemExit("V datech chybí descriptions.")

    # Zdrojový jazyk = první s obsahem (typicky en)
    source_lang = "en"
    source_desc = next((d for d in descriptions if d.get("language") == source_lang), descriptions[0])
    target_languages = list({d.get("language") for d in descriptions if d.get("language")})

    # Pravidla: sk = obsah z cz; no = en; ta = en (bez překladu)
    USE_CZ_FOR = ["sk"]
    USE_EN_FOR = ["no", "ta"]

    print(f"Zdroj: {source_lang}, cílové jazyky: {target_languages}")
    print(f"Pravidla: {USE_CZ_FOR} = cz, {USE_EN_FOR} = en")

    out_descriptions = []
    for desc in descriptions:
        lang = desc.get("language") or "en"
        out = dict(desc)
        target = get_translator_target(lang)

        if lang == source_lang:
            out_descriptions.append(out)
            continue

        # no, ta → použít angličtinu (bez překladu)
        if lang in USE_EN_FOR:
            for key in ("title", "long_description", "seo_url", "seo_title", "seo_description"):
                if source_desc.get(key) is not None:
                    out[key] = source_desc[key]
            print(f"  [{lang}] = en (zkopírováno)")
            out_descriptions.append(out)
            continue

        # sk → použít obsah z češtiny (cz/cs)
        if lang in USE_CZ_FOR:
            cz_entry = next((d for d in out_descriptions if d.get("language") == "cs"), None)
            if cz_entry:
                for key in ("title", "long_description", "seo_url", "seo_title", "seo_description"):
                    if cz_entry.get(key) is not None:
                        out[key] = cz_entry[key]
                print(f"  [{lang}] = cz (zkopírováno)")
            else:
                # cs ještě nebyl zpracován – přeložíme en→sk a pak později opravíme, nebo přeložíme en→cs
                trans = GoogleTranslator(source=source_lang, target="cs")
                if source_desc.get("title"):
                    out["title"] = translate_text(trans, source_desc["title"])
                if source_desc.get("long_description"):
                    out["long_description"] = translate_text(trans, source_desc["long_description"])
                if source_desc.get("seo_url"):
                    out["seo_url"] = translate_text(trans, source_desc["seo_url"])
                if source_desc.get("seo_title") and str(source_desc.get("seo_title")).strip():
                    out["seo_title"] = translate_text(trans, source_desc["seo_title"])
                if source_desc.get("seo_description") and str(source_desc.get("seo_description")).strip():
                    out["seo_description"] = translate_text(trans, source_desc["seo_description"])
                print(f"  [{lang}] = cz (přeloženo en→cs)")
            out_descriptions.append(out)
            continue

        trans = GoogleTranslator(source=source_lang, target=target)

        # title
        if source_desc.get("title"):
            out["title"] = translate_text(trans, source_desc["title"])
            print(f"  [{lang}] title OK")
        time.sleep(0.3)

        # long_description
        if source_desc.get("long_description"):
            out["long_description"] = translate_text(trans, source_desc["long_description"])
            print(f"  [{lang}] long_description OK")
        time.sleep(0.3)

        # seo_url (obvykle jako text, přeložíme)
        if source_desc.get("seo_url"):
            out["seo_url"] = translate_text(trans, source_desc["seo_url"])
            print(f"  [{lang}] seo_url OK")
        time.sleep(0.3)

        # seo_title – přeložit jen když není null
        if source_desc.get("seo_title") is not None and str(source_desc.get("seo_title")).strip():
            out["seo_title"] = translate_text(trans, source_desc["seo_title"])
            print(f"  [{lang}] seo_title OK")
        time.sleep(0.2)

        # seo_description – přeložit jen když není null
        if source_desc.get("seo_description") is not None and str(source_desc.get("seo_description")).strip():
            out["seo_description"] = translate_text(trans, source_desc["seo_description"])
            print(f"  [{lang}] seo_description OK")
        time.sleep(0.2)

        out_descriptions.append(out)

    data["descriptions"] = out_descriptions
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nHotovo. Uloženo: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
