# Nastavení na Mac - Rychlý start

## ✅ Co je už připraveno:
- ✅ Node.js je nainstalován (v24.13.1)
- ✅ npm závislosti jsou nainstalovány
- ✅ Credentials soubor existuje (`upgates_credentials.json`)
- ✅ Startovací skript je připraven (`product-manager/start.sh`)

## 🚀 Jak spustit aplikaci:

### Možnost 1: Použít startovací skript
```bash
cd "/Users/alex08/Desktop/Cursor Git/Upgates/product-manager"
./start.sh
```

### Možnost 2: Klasický způsob
```bash
cd "/Users/alex08/Desktop/Cursor Git/Upgates/product-manager"
npm start
```

## 🌐 Po spuštění:
Aplikace bude dostupná na: **http://localhost:3333**

Otevřete tento odkaz v prohlížeči a můžete začít pracovat s produkty z Upgates API.

## 📝 Funkce aplikace:
- **Načíst produkty** - stáhne seznam produktů z Upgates API
- **Export JSON** - exportuje produkt jako JSON soubor
- **Import JSON** - nahraje upravený JSON soubor zpět do Upgates

## ⚠️ Poznámky:
- Aplikace běží na portu 3333 (pokud je port obsazený, můžete změnit v `server.js` nebo nastavit proměnnou `PORT`)
- Pro zastavení serveru stiskněte `Ctrl+C` v terminálu
- Credentials jsou uloženy v `upgates_credentials.json` (soubor je v `.gitignore`, takže se necommitne do gitu)

## 🔧 Pokud byste potřebovali znovu nainstalovat závislosti:
```bash
cd "/Users/alex08/Desktop/Cursor Git/Upgates/product-manager"
rm -rf node_modules
npm install
```
