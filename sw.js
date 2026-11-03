/* Service worker da Nanna Subito (gerado por _fonte/gerar.py).
   (1) habilita o "instalar app"; (2) abre offline depois da primeira visita; (3) guarda o ACESSO no Cache Storage,
   que é por origem e atravessa o isolamento do iPhone entre o Safari e o app instalado (o localStorage não atravessa).
   Rede primeiro, cache como reserva: com internet vem sempre a versão nova, sem ela continua funcionando.
   Subir a VERSÃO em gerar.py a cada mudança, senão o celular segue com o arquivo velho. */
const CACHE = 'nanna-v5';
const PASTAS = ["p3n8wa", "h6s2qe", "r9l4tm", "z5o7ck", "k8c3vd", "t2x9aa"];
const ARQS = ['conteudo.js', 'suoni/pancia.wav', 'suoni/rumore-bianco.wav', 'img/icones/icone-192.png', 'img/icones/favicon-32.png', 'img/icones/apple-touch-180.png',
  ...PASTAS.map(p => p + '/'), ...PASTAS.map(p => p + '/manifest.webmanifest')];
const CHAVE = '/__acesso__';
const VALIDOS = ['base', 'seno', 'lettino', 'orologio', 'consulente'];

async function gravarAcesso(itens) {
  try {
    const c = await caches.open(CACHE), r = await c.match(CHAVE);
    let antes = []; if (r) { try { antes = await r.json(); } catch (e) {} }
    const uniao = [...new Set([...(Array.isArray(antes) ? antes : []), ...itens.filter(i => VALIDOS.includes(i))])];
    await c.put(CHAVE, new Response(JSON.stringify(uniao), { headers: { 'content-type': 'application/json' } }));
    return uniao;
  } catch (e) { return itens; }
}

self.addEventListener('message', e => {
  const d = e.data || {};
  if (d.tipo === 'gravar-acesso' && Array.isArray(d.itens)) {
    e.waitUntil(gravarAcesso(d.itens).then(u => e.source && e.source.postMessage({ tipo: 'acesso', itens: u })));
  }
});

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.allSettled(ARQS.map(a => c.add(new Request(a, { cache: 'reload' }))))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  /* migra o acesso dos caches velhos antes de apagá-los: sem isso, cada publicação nova trancaria quem já comprou */
  e.waitUntil((async () => {
    const velhos = (await caches.keys()).filter(k => k !== CACHE && k.startsWith('nanna-'));
    for (const k of velhos) {
      try { const r = await (await caches.open(k)).match(CHAVE); if (r) { const v = await r.json(); if (Array.isArray(v) && v.length) await gravarAcesso(v); } } catch (e) {}
    }
    await Promise.all(velhos.map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  /* fontes do Google: cache primeiro (não mudam), para o app abrir bonito também sem internet */
  if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
    e.respondWith(caches.open(CACHE).then(async c => (await c.match(req)) || fetch(req).then(r => { c.put(req, r.clone()); return r; })));
    return;
  }
  if (url.origin !== location.origin || url.pathname === CHAVE) return;
  e.respondWith(
    fetch(new Request(req.url, { cache: 'no-store', credentials: 'same-origin' })).then(r => {
      if (r && r.ok) { const copia = r.clone(); caches.open(CACHE).then(c => c.put(req, copia)).catch(() => {}); }
      return r;
    }).catch(async () => {
      const exata = await caches.match(req, { ignoreSearch: true }); if (exata) return exata;
      /* offline sem cópia exata: cair no index da PRÓPRIA pasta de acesso, nunca na raiz trancada */
      const m = url.pathname.match(new RegExp('/(' + PASTAS.join('|') + ')(?:/|$)'));
      if (m) {
        const pasta = url.pathname.slice(0, m.index + m[0].length).replace(/\/?$/, '/');
        for (const alvo of [pasta, pasta + 'index.html']) { const r = await caches.match(alvo, { ignoreSearch: true }); if (r) return r; }
      }
      return Response.error();
    })
  );
});
