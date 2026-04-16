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

function formatApiError(body, fallback) {
  if (body == null) return fallback;
  if (typeof body === 'string') return body;
  if (Array.isArray(body.messages)) {
    const parts = body.messages.map((m) =>
      typeof m === 'object' && m !== null ? (m.message || m.text || m.error || JSON.stringify(m)) : String(m)
    );
    return parts.length ? parts.join('; ') : fallback;
  }
  if (typeof body.message === 'string') return body.message;
  if (typeof body.error === 'string') return body.error;
  return fallback || JSON.stringify(body);
}

// Base URL pro endpoint /products/code – správný formát: https://airteam.admin.s7.upgates.com/api/v2/products/code?codes=PS600;PS601
function productsCodeBaseUrl() {
  const creds = loadCredentials();
  return (creds.api_url_products_code || creds.api_url || apiUrl()).replace(/\/$/, '');
}

// Seznam produktů – endpoint Upgates: GET .../products/code?codes=PS600;PS601 (oddělovač je středník)
// GET /api/products?codes=PS600,PS601&page=1&limit=20 (uživatel může psát čárku, do Upgates jde středník)
app.get('/api/products', async (req, res) => {
  try {
    const base = productsCodeBaseUrl();
    const codesRaw = (req.query.codes ?? '').trim();
    const codesParam = codesRaw
      ? codesRaw.split(/[,;]/).map((c) => c.trim()).filter(Boolean).join(';')
      : '';
    const page = Math.max(1, parseInt(req.query.page, 10) || 1);
    const limit = Math.min(5000, Math.max(1, parseInt(req.query.limit, 10) || 5000));

    if (!codesParam) {
      const totalPages = 1;
      return res.json({
        items: [],
        total: 0,
        page: 1,
        limit,
        totalPages,
        upstream_url: null,
        message: 'Zadejte alespoň jeden kód (codes). Používá se endpoint /products/code?codes=PS600;PS601',
      });
    }

    const upgatesUrl = `${base}/products/code?codes=${codesParam}`;
    console.log('[products] req.query.codes=', req.query.codes, '→ Upgates:', upgatesUrl);
    const data = await request('GET', upgatesUrl);
    let list = Array.isArray(data) ? data : null;
    if (!list && data && typeof data === 'object') {
      list = data.data ?? data.products ?? data.items ?? null;
      if (list && !Array.isArray(list) && typeof list === 'object' && list.items) list = list.items;
    }
    if (!Array.isArray(list)) list = [];

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
      upstream_url: upgatesUrl,
    });
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    res.status(err.status || 500).json({ error: msg });
  }
});

// Detail produktu podle kódu (pro export) – stejný endpoint, parametr codes s jedním kódem
app.get('/api/products/by-code/:code', async (req, res) => {
  try {
    const base = productsCodeBaseUrl();
    const code = (req.params.code || '').trim();
    const codesParam = code || '';
    const upgatesQuery = new URLSearchParams();
    if (codesParam) upgatesQuery.set('codes', codesParam);
    const upgatesUrl = `${base}/products/code${upgatesQuery.toString() ? '?' + upgatesQuery.toString() : ''}`;
    const data = await request('GET', upgatesUrl);
    let list = Array.isArray(data) ? data : (data && (data.data || data.products)) || [];
    if (!Array.isArray(list)) list = [];
    const product = list[0] || null;
    if (!product) {
      return res.status(404).json({ error: 'Produkt nenalezen' });
    }
    res.json(product);
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    res.status(err.status || 500).json({ error: msg });
  }
});

// Seznam kategorií – endpoint Upgates: GET .../categories (stránky jsou součástí obsahu kategorií)
// Parametry Upgates: codes, code, ids, category_id, parent_id, active_yn, exclude_from_search_yn,
//   language, creation_time_from, last_update_time_from, page
app.get('/api/categories', async (req, res) => {
  try {
    const base = apiUrl();
    const page = Math.max(1, parseInt(req.query.page, 10) || 1);
    const limit = Math.min(5000, Math.max(1, parseInt(req.query.limit, 10) || 20));

    const upgatesParams = new URLSearchParams();
    upgatesParams.set('page', String(page));

    const codesRaw = (req.query.codes ?? req.query.code ?? '').trim();
    if (codesRaw) {
      const codesParam = codesRaw.split(/[,;]/).map((c) => c.trim()).filter(Boolean).join(';');
      if (codesParam) upgatesParams.set('codes', codesParam);
    }
    if (req.query.ids) upgatesParams.set('ids', String(req.query.ids).trim());
    if (req.query.category_id) upgatesParams.set('category_id', String(req.query.category_id).trim());
    if (req.query.parent_id !== undefined && req.query.parent_id !== '') upgatesParams.set('parent_id', String(req.query.parent_id).trim());
    if (req.query.active_yn !== undefined && req.query.active_yn !== '') upgatesParams.set('active_yn', String(req.query.active_yn));
    if (req.query.exclude_from_search_yn !== undefined && req.query.exclude_from_search_yn !== '') upgatesParams.set('exclude_from_search_yn', String(req.query.exclude_from_search_yn));
    if (req.query.language) upgatesParams.set('language', String(req.query.language).trim());
    if (req.query.creation_time_from) upgatesParams.set('creation_time_from', String(req.query.creation_time_from).trim());
    if (req.query.last_update_time_from) upgatesParams.set('last_update_time_from', String(req.query.last_update_time_from).trim());

    const upgatesUrl = `${base}/categories?${upgatesParams.toString()}`;
    console.log('[categories] GET', upgatesUrl);
    const data = await request('GET', upgatesUrl);
    let list = Array.isArray(data) ? data : null;
    let totalFromApi = null;
    if (!list && data && typeof data === 'object') {
      list = data.data ?? data.categories ?? data.items ?? null;
      if (list && !Array.isArray(list) && typeof list === 'object' && list.items) list = list.items;
      totalFromApi = data.total ?? data.total_count ?? data.count ?? null;
    }
    if (!Array.isArray(list)) list = [];

    const total = totalFromApi != null ? Number(totalFromApi) : list.length;
    const totalPages = Math.max(1, Math.ceil(total / limit));
    const pageIndex = Math.min(page, totalPages);
    const offset = (pageIndex - 1) * limit;
    const items = totalFromApi != null ? list : list.slice(offset, offset + limit);

    res.json({
      items,
      total,
      page: pageIndex,
      limit,
      totalPages,
      upstream_url: upgatesUrl,
    });
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    res.status(err.status || 500).json({ error: msg });
  }
});

// Aktualizace kategorie (import JSON) – formát: { "categories": [ {...} ] }
// Zkoušíme POST (některé API používají POST pro update)
app.put('/api/categories/:id', async (req, res) => {
  try {
    const base = apiUrl();
    const id = req.params.id;
    const body = req.body;
    if (!body || typeof body !== 'object') {
      return res.status(400).json({ error: 'Očekáván JSON objekt' });
    }
    if (!Array.isArray(body.descriptions)) {
      return res.status(400).json({ error: 'V JSON chybí pole descriptions (pole objektů).' });
    }
    const categoryId = body.category_id != null ? body.category_id : id;
    const payload = { categories: [{ ...body, category_id: categoryId }] };
    const url = `${base}/categories`;
    console.log('[categories] PUT', url, 'category_id:', categoryId);
    await request('PUT', url, payload);
    res.json({ ok: true, id: categoryId });
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    res.status(err.status || 500).json({ error: msg });
  }
});

// Seznam článků – GET {api_url}/articles
// Parametry: id, creation_time_from, last_update_time_from, active_yn, language, category_code, with_subcategories_yn, page
app.get('/api/content', async (req, res) => {
  let upgatesUrl = '';
  try {
    const base = apiUrl();
    const page = Math.max(1, parseInt(req.query.page, 10) || 1);
    const limit = Math.min(5000, Math.max(1, parseInt(req.query.limit, 10) || 20));

    const upgatesParams = new URLSearchParams();
    upgatesParams.set('page', String(page));

    const idsRaw = (req.query.ids ?? '').trim();
    if (idsRaw) {
      const idsParam = idsRaw.split(/[,;]/).map((c) => c.trim()).filter(Boolean).join(';');
      if (idsParam) upgatesParams.set('id', idsParam);
    }
    if (req.query.content_id) upgatesParams.set('id', String(req.query.content_id).trim());
    if (req.query.active_yn !== undefined && req.query.active_yn !== '') upgatesParams.set('active_yn', String(req.query.active_yn));
    if (req.query.language) upgatesParams.set('language', String(req.query.language).trim());
    if (req.query.creation_time_from) upgatesParams.set('creation_time_from', String(req.query.creation_time_from).trim());
    if (req.query.last_update_time_from) upgatesParams.set('last_update_time_from', String(req.query.last_update_time_from).trim());
    if (req.query.category_code) upgatesParams.set('category_code', String(req.query.category_code).trim());
    if (req.query.with_subcategories_yn !== undefined && req.query.with_subcategories_yn !== '') upgatesParams.set('with_subcategories_yn', String(req.query.with_subcategories_yn));

    upgatesUrl = `${base}/articles?${upgatesParams.toString()}`;
    console.log('[content] GET', upgatesUrl);
    const data = await request('GET', upgatesUrl);
    const list = Array.isArray(data?.articles) ? data.articles : [];
    const currentPage = Number(data?.current_page) ?? page;
    const currentPageItems = Number(data?.current_page_items) ?? list.length;
    const totalPages = Number(data?.number_of_pages) ?? 1;
    const total = Number(data?.number_of_items) ?? list.length;

    res.json({
      items: list,
      total,
      page: currentPage,
      limit: currentPageItems,
      totalPages,
      upstream_url: upgatesUrl,
    });
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    const errBody = { error: msg, upstream_url: upgatesUrl };
    res.status(err.status || 500).json(errBody);
  }
});

// Aktualizace článku – PUT {api_url}/articles (ověř v dokumentaci)
app.put('/api/content/:id', async (req, res) => {
  try {
    const base = apiUrl();
    const id = req.params.id;
    const body = req.body;
    if (!body || typeof body !== 'object') {
      return res.status(400).json({ error: 'Očekáván JSON objekt' });
    }
    const contentId = body.content_id != null ? body.content_id : body.id != null ? body.id : id;
    const payload = { articles: [{ ...body, content_id: contentId }] };
    const url = `${base}/articles`;
    console.log('[content] PUT', url, 'content_id:', contentId);
    await request('PUT', url, payload);
    res.json({ ok: true, id: contentId, upstream_url: url, upstream_method: 'PUT' });
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    const url = `${apiUrl()}/articles`;
    res.status(err.status || 500).json({ error: msg, upstream_url: url, upstream_method: 'PUT' });
  }
});

// Aktualizace produktu (import JSON) – formát dle upload_product.ps1: PUT /products s payload { products: [ { product_id, code, descriptions } ] }
app.put('/api/products/:id', async (req, res) => {
  try {
    const base = apiUrl();
    const id = req.params.id;
    const body = req.body;
    if (!body || typeof body !== 'object') {
      return res.status(400).json({ error: 'Očekáván JSON objekt' });
    }
    const productId = body.product_id ?? body.id ?? id;
    const code = body.code;
    const descriptions = body.descriptions;
    if (!Array.isArray(descriptions)) {
      return res.status(400).json({ error: 'V JSON chybí pole descriptions (pole objektů).' });
    }
    const payload = {
      products: [{ product_id: productId, code: code || String(id), descriptions }],
    };
    await request('PUT', `${base}/products`, payload);
    res.json({ ok: true, id: productId });
  } catch (err) {
    console.error(err);
    const msg = formatApiError(err.body, err.message || 'Chyba API');
    res.status(err.status || 500).json({ error: msg });
  }
});

const PORT = process.env.PORT || 3333;
app.listen(PORT, () => {
  console.log(`Upgates Product Manager: http://localhost:${PORT}`);
});
