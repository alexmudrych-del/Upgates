# Upgates Product Manager

Single-page aplikace: seznam produktů z Upgates API, filtrování, Export JSON a Import JSON zpět do Upgates.

## Požadavky

- Node.js 18+
- Credentials v `../upgates_credentials.json` (složka nad `product-manager`)

## Instalace a spuštění

```bash
cd product-manager
npm install
npm start
```

Aplikace běží na **http://localhost:3333**.

## Funkce

- **Načíst produkty** – stáhne seznam produktů z Upgates API.
- **Filtr** – filtrování podle kódu nebo názvu (title).
- **Export JSON** – u každého produktu tlačítko „Export JSON“: stáhne kompletní detail produktu a uloží jako soubor `{kód}.json`.
- **Import JSON** – tlačítko „Import JSON“: vyberete soubor `.json` (dříve exportovaný nebo upravený) a nahraje se zpět do Upgates (PUT na daný produkt).

## Řešení problémů s `npm install`

Pokud se objeví chyby **TAR_ENTRY_ERROR**, **EBADF**, **EBUSY** nebo **EPERM**:

1. **Projekt na Google Disku / OneDrive** – synchronizace při zápisu do `node_modules` často způsobuje tyto chyby. Nejspolehlivější: zkopíruj projekt do lokální složky (např. `C:\Projects\Upgates`) a tam spusť `npm install` a `npm start`.
2. **Vyčistit cache a znovu nainstalovat** (v `product-manager`):
   ```bash
   npm cache clean --force
   rmdir /s /q node_modules
   npm install
   ```
   Před `rmdir` zavři Cursor (nebo aspoň terminál v této složce), aby nic nedrželo složku.
3. **Antivirus** – dočasně vypni real-time skenování pro složku projektu, nebo přidej výjimku pro `node_modules`.

## Poznámky

- API vrací omezený počet produktů na jeden požadavek (např. 50). Pro větší e-shopy může být potřeba rozšířit server o stránkování.
- Import přepisuje produkt v Upgates daty z JSON – používejte s rozvahou, ideálně po zálohování (Export).
