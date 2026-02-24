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
- **Base URL:** hodnota `api_url` bez koncové lomítko (např. `https://.../api/v2`).

---

## 2. Externí Upgates API v2 (co volá backend)

Backend volá pouze tyto endpointy. Přesné chování (limity, další parametry) je dáno dokumentací Upgates (např. Apiary).

| Metoda | URL | Popis |
|--------|-----|--------|
| GET | `{api_url}/products` | Seznam produktů. Žádné query parametry se z tohoto projektu neposílají (kromě by-code). |
| GET | `{api_url}/products?code={code}` | Jeden produkt podle kódu. Používá se v `/api/products/by-code/:code`. |
| PUT | `{api_url}/products/{id}` | Aktualizace produktu. Body = celý JSON objekt produktu. |

**Normalizace odpovědi GET /products:**

- Odpověď může být: pole `[]`, nebo objekt s `data`, nebo objekt s `products`.
- V kódu se vždy převede na pole: `Array.isArray(data) ? data : (data?.data ?? data?.products ?? [])`.

**Omezení:**

- Jeden request na `GET /products` (bez parametrů) vrací omezený počet záznamů (řádově desítky). Stránkování/filtrování na straně Upgates se z této aplikace nevolá.

---

## 3. Lokální proxy API (Express server, product-manager)

Base URL aplikace: `http://localhost:3333` (nebo `process.env.PORT`). Všechny route prefix: `/api`.

### 3.1 GET /api/products

**Účel:** Seznam produktů s volitelným filtrováním a stránkováním.

**Chování:**

1. Načte data z `GET {api_url}/products` (bez query parametrů).
2. Odpověď normalizuje na pole (viz výše).
3. Aplikuje **lokální filtry** (v paměti) podle query parametrů.
4. Aplikuje **stránkování** (slice pole).
5. Vrátí JSON s `items`, `total`, `page`, `limit`, `totalPages`.

**Query parametry:**

| Parametr | Typ | Výchozí | Popis |
|----------|-----|---------|--------|
| `q` | string | — | Vyhledávání: produkt musí obsahovat `q` v názvu (title) NEBO v kódu (code). Case-insensitive, substring match. |
| `title` | string | — | Filtrování podle názvu: `descriptions[0].title` nebo `code` musí obsahovat zadaný řetězec (case-insensitive). |
| `code` | string | — | Filtrování podle kódu: `product.code` musí obsahovat zadaný řetězec (case-insensitive). |
| `page` | integer | 1 | Číslo stránky (≥ 1). |
| `limit` | integer | 20 | Počet položek na stránku. Clamp: 1–100. |

**Kombinace filtrů:** Všechny zadané filtry se skládají logicky AND (musí platit `title` AND `code` AND `q`). Prázdný parametr se ignoruje.

**Definice „názvu“ produktu v kódu:**  
`getProductTitle(p) = (p.descriptions?.[0]?.title) || p.code || ''`

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

1. Volá `GET {api_url}/products?code={encodeURIComponent(code)}`.
2. Z odpovědi vezme první prvek z normalizovaného pole.
3. Pokud žádný není → 404.

**Odpověď 200:** Jeden produkt (JSON objekt).  
**Odpověď 404:** `{ "error": "Produkt nenalezen" }`.

---

### 3.3 PUT /api/products/:id

**Účel:** Aktualizace produktu v Upgates (import JSON).

**Request:** Body = JSON objekt (celý produkt). `Content-Type: application/json`.

**Chování:**

1. Ověří, že body je objekt.
2. Volá `PUT {api_url}/products/{id}` s tímto tělem.
3. Na úspěch vrací `{ "ok": true, "id": "<id>" }`.

**Chyby:** 400 pokud body není objekt; jinak status a tělo z Upgates nebo 500.

---

## 4. Shrnutí datových toků

```
Klient (prohlížeč)
    → GET /api/products?q=...&page=...&limit=...
    → server načte GET {api_url}/products
    → server filtruje (title, code, q) a stránkuje
    → odpověď { items, total, page, limit, totalPages }

Klient
    → GET /api/products/by-code/:code
    → server GET {api_url}/products?code=...
    → první prvek → 200 nebo 404

Klient
    → PUT /api/products/:id + JSON body
    → server PUT {api_url}/products/:id + body
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

## 6. Rozšíření v budoucnu

- **Více stránek z Upgates:** Pokud Upgates API podporuje `page`/`offset`/`limit`, předat je do `GET {api_url}/products` a případně sloučit více requestů před aplikací lokálních filtrů.
- **Další filtry:** Přidat další query parametry a rozšířit `filterProducts()` podle potřeb (např. kategorie, sklad).

Tento soubor slouží jako jediný striktní technický zdroj pravdy pro chování Upgates API a lokálního proxy v tomto projektu.
