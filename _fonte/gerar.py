# Monta o app da Nanna Subito a partir de _fonte/: o conteúdo em conteudo.js e uma cópia do app em cada pasta de
# acesso. O acesso vai no CAMINHO (nunca na query): a query some quando a pessoa instala o PWA e ela perde o que
# comprou. Subir VERSAO a cada mudança publicada, senão o celular segue com o arquivo velho.
#   python _fonte/gerar.py
import json, os, re

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)

# pasta -> o que ela libera. Cada compra leva ao link da sua pasta; o aparelho soma tudo o que já abriu.
PASTAS = {
    'p3n8wa': ['base'],                                              # front: rituale, suoni, SOS, piano 7 notti
    'h6s2qe': ['base', 'seno'],                                      # bump Senza seno
    'r9l4tm': ['base', 'lettino'],                                   # bump Nel lettino
    'z5o7ck': ['base', 'orologio'],                                  # bump Orologio della Nanna
    'k8c3vd': ['base', 'consulente'],                                # upsell Consulente del Sonno
    't2x9aa': ['base', 'seno', 'lettino', 'orologio', 'consulente'], # teste interno: tudo liberado (fora do ar, ver .gitignore)
}
# checkouts avulsos dos pacotes, abertos pelo cadeado dentro do app (Hotmart em euro; sem ?checkoutMode=10 o banner some)
CHECKOUT = {k: f'https://pay.hotmart.com/{c}?checkoutMode=10' for k, c in
            {'seno': 'R108290415K', 'lettino': 'O108290587G', 'orologio': 'W108290592I', 'consulente': 'F108290595O'}.items()}
VERSAO = 3

c = json.load(open(os.path.join(AQUI, 'conteudo', 'conteudo.json'), encoding='utf-8'))
c.pop('_nota', None)
for k, notti in c['piano']['notti'].items():
    assert len(notti) == 7 and k in c['piano']['partenze'], f'partenza {k}: 7 notti'
assert len(c['pacchetti']['seno']['notti']) == 7
assert set(c['pacchetti']['consulente']['consigli']) == {f'{a}-{r}' for a in ('facile', 'lungo', 'braccio') for r in ('poco', 'medio', 'tanti')}
for nome in ('pancia', 'rumore-bianco', 'pioggia', 'ninna-1', 'ninna-2', 'ninna-cascata'):
    assert os.path.exists(os.path.join(APP, 'suoni', nome + '.wav')), f'falta o som {nome} (rodar _fonte/sons.py e _fonte/tratar.py)'

with open(os.path.join(APP, 'conteudo.js'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('/* gerado por _fonte/gerar.py a partir de _fonte/conteudo/ */\nwindow.CONTEUDO=' + json.dumps(c, ensure_ascii=False, separators=(',', ':')) + ';\n')

modelo = open(os.path.join(AQUI, 'app.html'), encoding='utf-8').read()

def pagina(acesso, raiz):
    s = modelo.replace('__ACESSO__', json.dumps(acesso)).replace('__RAIZ__', raiz)
    for k, v in CHECKOUT.items():
        s = s.replace(f'__CK_{k.upper()}__', v)
    assert not re.search(r'__[A-Z_]+__', s), 'sobrou marcador no modelo'
    return s

def manifesto(raiz):
    pre = '' if raiz == './' else '../'
    return {
        'name': 'Nanna Subito', 'short_name': 'Nanna Subito', 'lang': 'it',
        'description': 'Il rituale della nanna, i suoni che non si fermano e il piano di 7 notti.',
        'start_url': './', 'scope': raiz, 'display': 'standalone', 'orientation': 'portrait',
        'background_color': '#eef6fc', 'theme_color': '#d3eafa',
        'icons': [
            {'src': pre + 'img/icones/icone-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': pre + 'img/icones/icone-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': pre + 'img/icones/icone-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }

# raiz: sem acesso (mostra o aviso de abrir pelo link do e-mail, a não ser que o aparelho já tenha acesso guardado)
open(os.path.join(APP, 'index.html'), 'w', encoding='utf-8', newline='\n').write(pagina([], './'))
json.dump(manifesto('./'), open(os.path.join(APP, 'manifest.webmanifest'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for pasta, acesso in PASTAS.items():
    os.makedirs(os.path.join(APP, pasta), exist_ok=True)
    open(os.path.join(APP, pasta, 'index.html'), 'w', encoding='utf-8', newline='\n').write(pagina(acesso, '../'))
    json.dump(manifesto('../'), open(os.path.join(APP, pasta, 'manifest.webmanifest'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

sw = open(os.path.join(AQUI, 'sw.js'), encoding='utf-8').read()
sw = sw.replace('__VERSAO__', str(VERSAO)).replace('__PASTAS__', json.dumps(list(PASTAS)))
open(os.path.join(APP, 'sw.js'), 'w', encoding='utf-8', newline='\n').write(sw)
open(os.path.join(APP, '.nojekyll'), 'w').close()
open(os.path.join(APP, '.gitignore'), 'w', encoding='utf-8', newline='\n').write(
    '# pasta de teste interno com tudo liberado: só local, nunca no ar\nt2x9aa/\n# áudios brutos trazidos pelo Vini, antes do tratamento\n_fonte/brutos/\n')
print('ok:', len(PASTAS), 'pastas, conteudo.js com', os.path.getsize(os.path.join(APP, 'conteudo.js')) // 1024, 'KB, versão', VERSAO)
