# Nahrání repozitáře na GitHub

## Stav

- Lokální repozitář je připraven (větev `main`, jeden commit).
- Soubor `upgates_credentials.json` je v `.gitignore` a **nebude** nahrán na GitHub.

## Kroky

### 1. Vytvořte repozitář na GitHubu

1. Přihlaste se na [github.com](https://github.com).
2. Klikněte **+** → **New repository**.
3. Zadejte název (např. `Upgates`).
4. **Nevyplňujte** README, .gitignore ani licenci (projekt už je má).
5. Klikněte **Create repository**.

### 2. Připojte remote a pushněte

Na příkazové řádce v složce projektu spusťte (nahraďte `VAS_GITHUB_USER` a `Upgates` svým údaji):

```bash
git remote add origin https://github.com/VAS_GITHUB_USER/Upgates.git
git push -u origin main
```

Pokud používáte SSH:

```bash
git remote add origin git@github.com:VAS_GITHUB_USER/Upgates.git
git push -u origin main
```

### 3. Ověření

- Na GitHubu uvidíte všechny soubory kromě `upgates_credentials.json`.
- Credentials si každý vývojář doplní lokálně podle `upgates_credentials.json.example`.
