# Upgates API – technická reference

Dokument popisuje **externí Upgates API v2** (e‑shop platforma) a **lokální proxy API** v projektu (product-manager). Striktně technické.

---

## 1. Autentizace vůči Upgates API

- **Metoda:** HTTP Basic Auth.
- **Credential soubor:** `upgates_credentials.json` (v kořeni projektu, v `.gitignore`).
- **Formát souboru:**
  ```json
  {
    "api_url": "https://VASPROJEKT.admin.server.upgates.com/api/v2",
    "login": "vas_login",
    "api_key": "vas_api_klic"
  }
  ```
- **Header:** `Authorization: Basic BASE64(login:api_key)`.
- **Požadavky:** `Accept: application/json`, `Content-Type: application/json` (u PUT/POST).
- **Base URL:** hodnota `api_url` bez koncové lomítko (např. `https://airteam.admin.s7.upgates.com/api/v2`).
- **Endpoint pro produkty podle kódů:** používá se `api_url` (nebo volitelně `api_url_products_code`). V parametru `codes` se více kódů odděluje **středníkem** (`;`).

---

## 2. Externí Upgates API v2 (co volá backend)

Backend volá pouze tyto endpointy.

| Metoda | URL | Popis |
|--------|-----|--------|
| GET | `{api_url}/products/code?codes=...` | Seznam produktů podle kódů. Parametr `codes`: jeden kód nebo více oddělených **středníkem** (např. `PS600` nebo `PS600;PS601`). |
| PUT | `{api_url}/products` | Aktualizace produktu. Body = `{ "products": [ { "product_id", "code", "descriptions" } ] }`. (Reference: upload_product.ps1) |
| GET | `{api_url}/categories` | Seznam kategorií (stránky jsou součástí obsahu kategorií). |

**Příklad (správný link):** `https://airteam.admin.s7.upgates.com/api/v2/products/code?codes=PS600;PS601`

**Normalizace odpovědi GET /products/code:**

- Odpověď může být: pole `[]`, nebo objekt s `data` / `products` / `items`.
- V kódu se vždy převede na pole.

---

## 3. Lokální proxy API (Express server, product-manager)

Base URL aplikace: `http://localhost:3333` (nebo `process.env.PORT`). Všechny route prefix: `/api`.

### 3.1 GET /api/products

**Účel:** Seznam produktů podle kódů (parametr `codes`) se stránkováním.

**Chování:**

1. Načte data z `GET {api_url}/products/code?codes={codes}`. Hodnota `codes` = query parametr; uživatel může zadat kódy oddělené čárkou nebo středníkem, do Upgates API jde vždy **středník** (např. `PS600;PS601`).
2. Odpověď normalizuje na pole.
3. Aplikuje **stránkování** (slice pole) podle `page` a `limit`.
4. Vrátí JSON s `items`, `total`, `page`, `limit`, `totalPages`.

**Query parametry:**

| Parametr | Typ | Výchozí | Popis |
|----------|-----|---------|--------|
| `codes` | string | — | Kódy produktů: jeden kód nebo více oddělených čárkou/středníkem (např. `PS600` nebo `PS600, PS601`). Do Upgates se posílá se středníkem: `PS600;PS601`. |
| `page` | integer | 1 | Číslo stránky (≥ 1). |
| `limit` | integer | 5000 | Počet položek na stránku. Clamp: 1–5000. |

**Odpověď 200:**

```json
{
  "items": [ /* pole produktů pro aktuální stránku */ ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "totalPages": 8
}
```

- `total` = počet položek po filtraci (před stránkováním).
- `page` = skutečně vrácená stránka (může být upravena, pokud `page` > `totalPages`).
- Chyby: 4xx/5xx podle chyby z Upgates nebo 500; body `{ "error": "string" }`.

---

### 3.2 GET /api/products/by-code/:code

**Účel:** Jeden produkt podle kódu (pro export).

**Chování:**

1. Volá `GET {api_url}/products/code?codes={code}`.
2. Z odpovědi vezme první prvek z normalizovaného pole.
3. Pokud žádný není → 404.

**Odpověď 200:** Jeden produkt (JSON objekt).  
**Odpověď 404:** `{ "error": "Produkt nenalezen" }`.

---

### 3.3 PUT /api/products/:id

**Účel:** Aktualizace produktu v Upgates (import JSON). Formát volání odpovídá referenčnímu skriptu **`upload_product.ps1`**.

**Request:** Body = JSON objekt produktu (např. exportovaný z aplikace). Musí obsahovat alespoň **`descriptions`** (pole); dále se použijí `product_id`/`id` a `code`.

**Chování:**

1. Ověří, že body je objekt a má pole `descriptions` (pole).
2. Sestaví payload dle **upload_product.ps1**: `{ "products": [ { "product_id", "code", "descriptions" } ] }`.
3. Volá **`PUT {api_url}/products`** (bez :id v path) s tímto payloadem.
4. Na úspěch vrací `{ "ok": true, "id": "<product_id>" }`.

**Chyby:** 400 pokud body není objekt nebo chybí `descriptions`; jinak status a zpráva z Upgates nebo 500.

---

## 4. Shrnutí datových toků

```
Klient (prohlížeč)
    → GET /api/products?codes=PS600,PS601&page=...&limit=...
    → server načte GET {api_url}/products/code?codes=PS600,PS601
    → server stránkuje a vrací { items, total, page, limit, totalPages }

Klient
    → GET /api/products/by-code/:code
    → server GET {api_url}/products/code?codes=...
    → první prvek → 200 nebo 404

Klient
    → PUT /api/products/:id + JSON body (produkt s descriptions)
    → server sestaví { products: [ { product_id, code, descriptions } ] }, PUT {api_url}/products
    → 200 { ok, id } nebo chyba
```

---

## 5. Důležité konstanty v kódu

| Konstanta | Hodnota | Soubor |
|-----------|---------|--------|
| Cesta k credentials | `path.join(__dirname, '..', 'upgates_credentials.json')` | server.js |
| Port | `process.env.PORT \|\| 3333` | server.js |
| Max limit stránkování | 100 | server.js |
| Výchozí limit | 20 | server.js |

---

## 6. Stránky (Pages) – poznámka

**Stránky v Upgates jsou součástí obsahu kategorií.** Pro práci se stránkami je třeba použít API kategorií.

- **Reference:** [Seznam kategorií – Upgates API v2](https://upgatesapiv2.docs.apiary.io/#reference/kategorie/kategorie/seznam-kategorii)

---

### 6.1 GET /api/categories

**Účel:** Seznam kategorií (stránky jsou součástí obsahu kategorií) se stránkováním a filtry.

**Chování:**

1. Volá `GET {api_url}/categories` s předanými parametry.
2. Odpověď normalizuje na pole (podobně jako u produktů).
3. Aplikuje stránkování podle `page` a `limit`.
4. Vrátí JSON s `items`, `total`, `page`, `limit`, `totalPages`.

**Query parametry** (předávány do Upgates API):

| Parametr | Typ | Popis |
|----------|-----|-------|
| `page` | integer | Číslo stránky. |
| `limit` | integer | Počet položek na stránku (1–5000). |
| `codes` | string | Kódy kategorií oddělené čárkou nebo středníkem (do Upgates jde středník). |
| `parent_id` | integer | ID nadřazené kategorie. |
| `active_yn` | bool | `true` / `false` – aktivní / neaktivní. |
| `language` | string | Jazyk (cs, en, sk, …). |
| `creation_time_from` | date | Pouze kategorie vytvořené od data. |
| `last_update_time_from` | date | Pouze kategorie změněné od data. |
| `ids` | string | ID kategorií oddělená středníkem. |
| `category_id` | integer | ID kategorie. |
| `exclude_from_search_yn` | bool | Vyřadit z vyhledávání. |

**Odpověď 200:** Stejný formát jako `/api/products` (`items`, `total`, `page`, `limit`, `totalPages`).

---

## 7. Rozšíření v budoucnu

- **Více stránek z Upgates:** Pokud Upgates API podporuje `page`/`offset`/`limit`, předat je do `GET {api_url}/products` a případně sloučit více requestů před aplikací lokálních filtrů.
- **Další filtry:** Přidat další query parametry a rozšířit `filterProducts()` podle potřeb (např. kategorie, sklad).

Tento soubor slouží jako jediný striktní technický zdroj pravdy pro chování Upgates API a lokálního proxy v tomto projektu.
