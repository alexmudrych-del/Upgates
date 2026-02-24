/**
 * Upgates Product Manager – backend
 * Proxy k Upgates API (credentials pouze na serveru).
 */
const path = require('path');
const fs = require('fs');
const http = require('http');
const https = require('https');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

const CREDS_PATH = path.join(__dirname, '..', 'upgates_credentials.json');

function loadCredentials() {
  const raw = fs.readFileSync(CREDS_PATH, 'utf8');
  return JSON.parse(raw);
}

function request(method, url, body = null) {
  const u = new URL(url);
  const isHttps = u.protocol === 'https:';
  const lib = isHttps ? https : http;
  const creds = loadCredentials();
  const auth = Buffer.from(`${creds.login}:${creds.api_key}`).toString('base64');

  const opts = {
    hostname: u.hostname,
    port: u.port || (isHttps ? 443 : 80),
    path: u.pathname + u.search,
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Basic ${auth}`,
    },
  };
  if (body && (method === 'PUT' || method === 'POST')) {
    opts.headers['Content-Length'] = Buffer.byteLength(JSON.stringify(body));
  }

  return new Promise((resolve, reject) => {
    const req = lib.request(opts, (res) => {
      let data = '';
      res.on('data', (ch) => (data += ch));
      res.on('end', () => {
        try {
          const json = data ? JSON.parse(data) : null;
          if (res.statusCode >= 400) {
            reject({ status: res.statusCode, body: json || data });
          } else {
            resolve(json);
          }
        } catch (e) {
          if (res.statusCode >= 400) reject({ status: res.statusCode, body: data });
          else resolve(data);
        }
      });
    });
    req.on('error', reject);
    if (body && (method === 'PUT' || method === 'POST')) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

function apiUrl() {
  return loadCredentials().api_url.replace(/\/$/, '');
}

function getProductTitle(p) {
  const d = (p.descriptions || [])[0];
  return (d && d.title) || p.code || '';
}

function filterProducts(list, query) {
  const title = (query.title || '').trim().toLowerCase();
  const code = (query.code || '').trim().toLowerCase();
  const q = (query.q || '').trim().toLowerCase();
  if (!title && !code && !q) return list;
  return list.filter((p) => {
    const pTitle = getProductTitle(p).toLowerCase();
    const pCode = (p.code || '').toLowerCase();
    const matchTitle = !title || pTitle.includes(title);
    const matchCode = !code || pCode.includes(code);
    const matchQ = !q || pTitle.includes(q) || pCode.includes(q);
    return matchTitle && matchCode && matchQ;
  });
}

// Seznam produktů – podpora filtrů (title, code, q) a stránkování (page, limit)
// GET /api/products?title=...&code=...&q=...&page=1&limit=20
app.get('/api/products', async (req, res) => {
  try {
    const base = apiUrl();
    const data = await request('GET', `${base}/products`);
    let list = Array.isArray(data) ? data : (data && (data.data || data.products)) || [];
    list = Array.isArray(list) ? list : [];

    const title = (req.query.title ?? '').trim();
    const code = (req.query.code ?? '').trim();
    const q = (req.query.q ?? '').trim();
    const page = Math.max(1, parseInt(req.query.page, 10) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit, 10) || 20));

    list = filterProducts(list, { title, code, q });
    const total = list.length;
    const totalPages = Math.max(1, Math.ceil(total / limit));
    const pageIndex = Math.min(page, totalPages);
    const offset = (pageIndex - 1) * limit;
    const items = list.slice(offset, offset + limit);

    res.json({
      items,
      total,
      page: pageIndex,
      limit,
      totalPages,
    });
  } catch (err) {
    console.error(err);
    res.status(err.status || 500).json({ error: err.body || err.message || 'Chyba API' });
  }
});

// Detail produktu podle kódu (pro export)
app.get('/api/products/by-code/:code', async (req, res) => {
  try {
    const base = apiUrl();
    const code = encodeURIComponent(req.params.code);
    const data = await request('GET', `${base}/products?code=${code}`);
    const list = Array.isArray(data) ? data : (data && (data.data || data.products)) || [];
    const product = list[0] || null;
    if (!product) {
      return res.status(404).json({ error: 'Produkt nenalezen' });
    }
    res.json(product);
  } catch (err) {
    console.error(err);
    res.status(err.status || 500).json({ error: err.body || err.message || 'Chyba API' });
  }
});

// Aktualizace produktu (import JSON)
app.put('/api/products/:id', async (req, res) => {
  try {
    const base = apiUrl();
    const id = req.params.id;
    const body = req.body;
    if (!body || typeof body !== 'object') {
      return res.status(400).json({ error: 'Očekáván JSON objekt' });
    }
    await request('PUT', `${base}/products/${id}`, body);
    res.json({ ok: true, id });
  } catch (err) {
    console.error(err);
    res.status(err.status || 500).json({ error: err.body || err.message || 'Chyba API' });
  }
});

const PORT = process.env.PORT || 3333;
app.listen(PORT, () => {
  console.log(`Upgates Product Manager: http://localhost:${PORT}`);
});
