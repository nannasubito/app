# Trata os áudios que o Vini trouxe (_fonte/brutos/, fora do git) e grava os sons do app em suoni/:
# corta as pontas sujas (fade, intro), acha o ponto em que o som mais se parece com o começo e emenda ali
# com um crossfade, para a volta do loop não ter corte nem pulo de melodia. Sai WAV mono 22 kHz (o MP3 deixa
# um silêncio a cada volta) com volume igualado. Não toca nada: a escolha do trecho é por análise.
#   python _fonte/tratar.py   (precisa de ffmpeg no PATH)
import os, subprocess
import numpy as np
from scipy.io import wavfile

AQUI = os.path.dirname(os.path.abspath(__file__))
BRUTOS = os.path.join(AQUI, 'brutos')
SAIDA = os.path.join(os.path.dirname(AQUI), 'suoni')
SR = 22050

# nome no app: (arquivo bruto, corte no começo s, corte no fim s, crossfade s, nível RMS dBFS, como achar a volta)
# volta: 'tudo' (ruído: o trecho inteiro), 'ritmo' (batida: pelo envelope de volume), 'notas' (música: pelas notas)
SONS = {
    'pioggia':       ('pioggia.mp4',       0.3, 0.2, 1.5, -24, 'tudo'),
    'pancia':        ('pancia.mp4',        0.6, 0.2, 0.25, -22, 'ritmo'),
    'ninna-1':       ('ninna-1.mp4',       0.2, 0.9, 1.0, -24, 'tudo'),   # 10 s sem repetição de melodia: o trecho inteiro
    'ninna-2':       ('ninna-2.mp4',       0.2, 0.3, 1.0, -24, 'tudo'),   # idem, 15 s
    'ninna-cascata': ('ninna-cascata.mp4', 1.6, 0.3, 0.8, -24, 'notas'),
}

def ler(arq):
    tmp = os.path.join(BRUTOS, '_tmp.wav')
    subprocess.run(['ffmpeg', '-nostats', '-loglevel', 'error', '-y', '-i', os.path.join(BRUTOS, arq), '-vn', '-ac', '1', '-ar', str(SR), tmp], check=True)
    _, y = wavfile.read(tmp); os.remove(tmp)
    return y.astype(float) / 32768

def envelope(y, passo):
    n = len(y) // passo
    return np.sqrt(np.mean(y[:n * passo].reshape(n, passo) ** 2, axis=1))

def cromas(y, passo):
    """as 12 notas (classes de altura) por quadro de 10 ms, para comparar melodia e harmonia."""
    jan = 4096; w = np.hanning(jan); f = np.fft.rfftfreq(jan, 1 / SR)
    ok = (f > 80) & (f < 4000); pc = np.round(12 * np.log2(f[ok] / 261.63)).astype(int) % 12
    out = []
    for i in range(0, len(y) - jan, passo):
        m = np.abs(np.fft.rfft(y[i:i + jan] * w))[ok]
        v = np.bincount(pc, weights=m, minlength=12); out.append(v / (np.linalg.norm(v) + 1e-12))
    return np.array(out)

def ponto_de_volta(y, xf, modo):
    """o fim do loop: onde o som mais se parece com o começo (1,5 s), entre 55% do trecho e o fim."""
    passo = SR // 100
    if modo == 'tudo':
        return len(y) - int(xf * SR) - 1, 0.0
    feat = cromas(y, passo) if modo == 'notas' else envelope(y, passo)[:, None]
    if modo == 'ritmo': feat = feat - feat.mean()
    mol = feat[:150].ravel()
    ini, fim = int(len(feat) * .55), len(feat) - 150 - int(xf * 100)
    melhor, nota = fim, -2
    for i in range(ini, fim):
        jan = feat[i:i + 150].ravel()
        c = float(np.dot(mol - mol.mean(), jan - jan.mean()) / (np.linalg.norm(mol - mol.mean()) * np.linalg.norm(jan - jan.mean()) + 1e-12))
        if c > nota: melhor, nota = i, c
    return melhor * passo, nota

for nome, (arq, a, b, xf, db, modo) in SONS.items():
    y = ler(arq)
    y = y[int(a * SR):len(y) - int(b * SR)]
    fim, nota = ponto_de_volta(y, xf, modo)
    nx = int(xf * SR)
    r = np.linspace(0, 1, nx)
    loop = y[:fim].copy()
    loop[:nx] = y[:nx] * np.sqrt(r) + y[fim:fim + nx] * np.sqrt(1 - r)   # o fim continua por baixo do começo
    loop = loop - loop.mean()
    loop *= 10 ** (db / 20) / np.sqrt(np.mean(loop ** 2))
    loop = np.clip(loop, -0.98, 0.98)
    wavfile.write(os.path.join(SAIDA, nome + '.wav'), SR, (loop * 32767).astype(np.int16))
    print(f'{nome}: {len(loop) / SR:.2f} s, volta em {fim / SR:.2f} s (semelhança {nota:.2f}), '
          f'{os.path.getsize(os.path.join(SAIDA, nome + ".wav")) // 1024} KB')
