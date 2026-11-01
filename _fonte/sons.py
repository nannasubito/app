# Gera os sons do app (sem gravação de terceiros, tudo sintetizado aqui): 30 s que emendam sem corte,
# WAV mono 16 kHz. WAV porque não tem o enchimento do MP3, que deixa um silêncio a cada volta do loop
# (o corte acorda o bebê). Volume moderado (RMS perto de -24 dBFS); o app ainda começa baixo.
#   python _fonte/sons.py
import os
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(os.path.dirname(AQUI), 'suoni')
os.makedirs(SAIDA, exist_ok=True)
SR, DUR, XF = 16000, 30.0, 1.5          # taxa, duração do loop, emenda (crossfade) em segundos
N, NX = int(SR * DUR), int(SR * XF)
rng = np.random.default_rng(7)

def filtro(x, tipo, f):
    return sosfilt(butter(4, f, btype=tipo, fs=SR, output='sos'), x)

def rosa(n):  # ruído rosa (1/f) pelo método de Voss simplificado no domínio da frequência
    X = np.fft.rfft(rng.standard_normal(n)); f = np.arange(len(X)); f[0] = 1
    return np.fft.irfft(X / np.sqrt(f), n)

def marrom(n):
    x = np.cumsum(rng.standard_normal(n)); return filtro(x - x.mean(), 'highpass', 20)

def emendar(gerar):
    """gera DUR+XF segundos e funde o fim no começo: a volta do loop fica sem emenda audível."""
    PR = SR  # 1 s descartado no começo: o filtro parte do zero e abafaria o início
    x = gerar(PR + N + NX)[PR:]
    r = np.linspace(0, 1, NX)
    ini = x[:NX] * np.sqrt(r) + x[N:N + NX] * np.sqrt(1 - r)
    return np.concatenate([ini, x[NX:N]])

def norm(x, db=-24):
    x = x - x.mean(); return x * (10 ** (db / 20) / np.sqrt(np.mean(x ** 2)))

def batida(n, bpm):  # 'lub-dub' grave, período que divide os 30 s (72 bpm = 36 batidas)
    t = np.arange(n) / SR; y = np.zeros(n); per = 60 / bpm
    for b in np.arange(1.0, n / SR, per):  # começa em 1 s: o 1º segundo é descartado
        for off, amp in ((0, 1.0), (0.28, .6)):
            i = int((b + off) * SR); m = min(n - i, int(.18 * SR))
            if m <= 0: continue
            tt = np.arange(m) / SR
            y[i:i + m] += amp * np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 28)
    return y

def sh(n):  # 'shh' ritmado: ruído agudo com envelope, 1 a cada 1,25 s (24 no loop)
    x = filtro(rng.standard_normal(n), 'bandpass', [1800, 6500]); t = np.arange(n) / SR
    fase = ((t - 1.0) % 1.25) / 1.25; env = np.clip(np.sin(np.pi * np.clip(fase / .8, 0, 1)), 0, 1) ** 1.5
    return x * (0.15 + env)

def motor(n, f0, ruido_banda):
    t = np.arange(n) / SR
    hum = sum(np.sin(2 * np.pi * f0 * k * t + k) / k for k in range(1, 6))
    return filtro(rng.standard_normal(n), 'bandpass', ruido_banda) * 1.0 + 0.08 * hum

def chuva(n):
    base = filtro(rosa(n), 'bandpass', [300, 5000])
    gotas = np.zeros(n); idx = rng.integers(0, n - 400, int(n / SR * 60))
    for i in idx:
        m = 300; tt = np.arange(m) / SR; gotas[i:i + m] += rng.uniform(.2, 1) * rng.standard_normal(m) * np.exp(-tt * 300)
    return base + 0.35 * filtro(gotas, 'highpass', 1500)

SONS = {
    'pancia': lambda n: norm(filtro(marrom(n), 'lowpass', 600)) * .6 + norm(batida(n, 72)) * .8,
    'rumore-bianco': lambda n: filtro(rosa(n), 'lowpass', 6000),
    'phon': lambda n: motor(n, 115, [400, 5000]),
    'aspirapolvere': lambda n: motor(n, 160, [700, 3500]) + 0.5 * filtro(rng.standard_normal(n), 'bandpass', [2500, 4000]),
    'pioggia': chuva,
    'sh-sh': sh,
}
# só o rumore bianco sai daqui; os outros sons vêm das gravações tratadas por _fonte/tratar.py
for nome, g in [('rumore-bianco', SONS['rumore-bianco'])]:
    y = norm(emendar(g))
    y = np.clip(y, -1, 1)
    wavfile.write(os.path.join(SAIDA, nome + '.wav'), SR, (y * 32767).astype(np.int16))
    print(nome, os.path.getsize(os.path.join(SAIDA, nome + '.wav')) // 1024, 'KB')
