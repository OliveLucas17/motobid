#!/usr/bin/env python3
"""
fipe.py — Consulta de precos via API FIPE + cache local
API: parallelum.com.br/fipe/api/v1/motos (gratuita, sem autenticacao)

Fluxo:
  1. Busca no cache local (data/fipe_cache.json) — valido por 7 dias
  2. Se nao encontrar, consulta a API FIPE
  3. Aplica fator de mercado (FIPE eh conservadora, mercado real ~15% acima)
  4. Fallback para tabela estatica do config.py
"""
import re, json, os, time
import urllib.request, urllib.parse
import time 
from datetime import datetime, timedelta
from utils import log

BASE_URL     = 'https://parallelum.com.br/fipe/api/v1/motos'
CACHE_FILE   = 'data/fipe_cache.json'
CACHE_HORAS  = 168        # 7 dias
FATOR_MERCADO = 1.15      # mercado real ~15% acima da FIPE


# ─── HTTP helper ──────────────────────────────────────────
def _get(url, timeout=10):
    time.sleep(0.5)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MotoBid/2.1'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        log(f'  [FIPE] erro HTTP: {e}')
        return None


# ─── Cache ────────────────────────────────────────────────
def _carregar_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except:
        return {}

def _salvar_cache(cache):
    os.makedirs('data', exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def _cache_valido(entry):
    try:
        salvo_em = datetime.fromisoformat(entry.get('ts', '2000-01-01'))
        return datetime.now() - salvo_em < timedelta(hours=CACHE_HORAS)
    except:
        return False


# ─── Busca na API FIPE ────────────────────────────────────
def _buscar_marcas():
    return _get(f'{BASE_URL}/marcas') or []

def _buscar_modelos(cod_marca):
    r = _get(f'{BASE_URL}/marcas/{cod_marca}/modelos')
    return (r or {}).get('modelos', [])

def _buscar_anos(cod_marca, cod_modelo):
    return _get(f'{BASE_URL}/marcas/{cod_marca}/modelos/{cod_modelo}/anos') or []

def _buscar_preco_fipe(cod_marca, cod_modelo, cod_ano):
    return _get(f'{BASE_URL}/marcas/{cod_marca}/modelos/{cod_modelo}/anos/{cod_ano}')

def _parse_valor(valor_str):
    """'R$ 15.000,00' -> 15000.0"""
    try:
        limpo = re.sub(r'[R$\s]', '', valor_str).replace('.', '').replace(',', '.')
        return float(limpo)
    except:
        return None

def _score_similaridade(nome_busca, nome_fipe):
    """Quanto os nomes se parecem. Retorna 0.0 a 1.0."""
    a = set(nome_busca.upper().split())
    b = set(nome_fipe.upper().split())
    if not a or not b:
        return 0.0
    intersecao = a & b
    return len(intersecao) / max(len(a), len(b))

def _encontrar_marca_fipe(nome_marca, marcas):
    """Acha o codigo da marca na lista FIPE."""
    nome_up = nome_marca.upper()
    for m in marcas:
        if nome_up in m.get('nome', '').upper():
            return m.get('codigo')
    return None

def _encontrar_modelo_fipe(nome_modelo, modelos):
    """Acha o modelo mais similar na lista FIPE."""
    melhor_score = 0
    melhor_cod   = None
    for m in modelos:
        s = _score_similaridade(nome_modelo, m.get('nome', ''))
        if s > melhor_score:
            melhor_score = s
            melhor_cod   = m.get('codigo')
    # Exige pelo menos 40% de similaridade
    return melhor_cod if melhor_score >= 0.4 else None


# ─── Funcao principal ─────────────────────────────────────
def get_preco(modelo, marca, ano_int=None, verbose=False):
    """
    Retorna (preco_mercado, fonte) onde:
      preco_mercado = valor FIPE * fator de mercado
      fonte = 'fipe_api' | 'fipe_cache' | 'tabela_estatica' | 'fallback'

    Exemplos:
      get_preco('HONDA CG 160 START', 'HONDA', 2024)
      get_preco('YAMAHA NMAX 160', 'YAMAHA')
    """
    cache_key = f'{marca.upper()}|{modelo.upper()}|{ano_int or "qualquer"}'
    cache     = _carregar_cache()

    # 1. Cache valido?
    if cache_key in cache and _cache_valido(cache[cache_key]):
        entry = cache[cache_key]
        if verbose:
            log(f'  [FIPE] cache: {modelo} = R${entry["fipe"]:.0f} (mercado R${entry["mercado"]:.0f})')
        return entry['mercado'], 'fipe_cache'

    # 2. Consulta API
    log(f'  [FIPE] consultando API: {marca} {modelo} {ano_int or ""}')
    marcas = _buscar_marcas()
    if not marcas:
        return _fallback(modelo, marca, cache, cache_key)

    cod_marca = _encontrar_marca_fipe(marca, marcas)
    if not cod_marca:
        log(f'  [FIPE] marca nao encontrada: {marca}')
        return _fallback(modelo, marca, cache, cache_key)

    modelos_fipe = _buscar_modelos(cod_marca)
    if not modelos_fipe:
        return _fallback(modelo, marca, cache, cache_key)

    # Remove a marca do nome do modelo para busca mais precisa
    # ex: 'HONDA CG 160 START' -> 'CG 160 START'
    modelo_sem_marca = re.sub(f'^{marca.upper()}\\s+', '', modelo.upper()).strip()
    cod_modelo = _encontrar_modelo_fipe(modelo_sem_marca, modelos_fipe)
    if not cod_modelo:
        log(f'  [FIPE] modelo nao encontrado: {modelo_sem_marca}')
        return _fallback(modelo, marca, cache, cache_key)

    anos_fipe = _buscar_anos(cod_marca, cod_modelo)
    if not anos_fipe:
        return _fallback(modelo, marca, cache, cache_key)

    # Escolhe o ano mais proximo do solicitado
    if ano_int:
        anos_fipe.sort(key=lambda a: abs(int(re.search(r'\d{4}', a.get('codigo','0')).group()) - ano_int)
                       if re.search(r'\d{4}', a.get('codigo','')) else 9999)
    cod_ano = anos_fipe[0].get('codigo')

    dados = _buscar_preco_fipe(cod_marca, cod_modelo, cod_ano)
    if not dados:
        return _fallback(modelo, marca, cache, cache_key)

    fipe_valor = _parse_valor(dados.get('valor', ''))
    if not fipe_valor:
        return _fallback(modelo, marca, cache, cache_key)

    mercado = round(fipe_valor * FATOR_MERCADO, -2)  # arredonda para centena

    # Salva no cache
    cache[cache_key] = {
        'fipe':       fipe_valor,
        'mercado':    mercado,
        'modelo_fipe': dados.get('modelo', ''),
        'ano_fipe':   dados.get('anoModelo', ''),
        'referencia': dados.get('mesReferencia', ''),
        'ts':         datetime.now().isoformat(),
    }
    _salvar_cache(cache)
    log(f'  [FIPE] OK: {dados.get("modelo","")} {dados.get("anoModelo","")} = R${fipe_valor:.0f} → mercado R${mercado:.0f}')
    return mercado, 'fipe_api'


def _fallback(modelo, marca, cache, cache_key):
    """Fallback para tabela estatica do config.py."""
    from config import PRECOS_REF, PRECO_FALLBACK
    modelo_up = modelo.upper().strip()

    # Tabela exata
    if modelo_up in PRECOS_REF:
        return PRECOS_REF[modelo_up], 'tabela_estatica'

    # Tabela parcial
    for chave, preco in PRECOS_REF.items():
        if chave in modelo_up or modelo_up in chave:
            return preco, 'tabela_parcial'

    # Fallback por marca
    marca_up = marca.upper()
    if marca_up in PRECO_FALLBACK:
        return PRECO_FALLBACK[marca_up], 'fallback_marca'

    return None, None


# ─── Atualizar cache para lista de modelos populares ──────
MODELOS_POPULARES = [
    ('HONDA', 'CG 160 START',   2024),
    ('HONDA', 'CG 160 FAN',     2024),
    ('HONDA', 'CG 160 TITAN',   2024),
    ('HONDA', 'BIZ 125',        2023),
    ('HONDA', 'PCX 160',        2023),
    ('HONDA', 'XRE 300',        2023),
    ('HONDA', 'BROS 160',       2023),
    ('YAMAHA', 'FACTOR 150',    2023),
    ('YAMAHA', 'FAZER 250',     2023),
    ('YAMAHA', 'NMAX 160',      2023),
    ('YAMAHA', 'XTZ 250',       2023),
    ('SUZUKI', 'YES 125',       2023),
    ('KAWASAKI', 'NINJA 300',   2023),
]

def atualizar_cache_popular():
    """Pre-popula o cache com os modelos mais comuns. Roda 1x por semana."""
    log('[FIPE] Atualizando cache de modelos populares...')
    ok = 0
    for marca, modelo, ano in MODELOS_POPULARES:
        nome_completo = f'{marca} {modelo}'
        preco, fonte = get_preco(nome_completo, marca, ano)
        if preco:
            log(f'  {nome_completo} {ano}: R${preco:.0f} ({fonte})')
            ok += 1
        time.sleep(0.5)  # respeita o rate limit da API
    log(f'[FIPE] Cache atualizado: {ok}/{len(MODELOS_POPULARES)} modelos')


if __name__ == '__main__':
    # Teste direto
    print('Testando API FIPE...')
    preco, fonte = get_preco('HONDA CG 160 START', 'HONDA', 2024, verbose=True)
    if preco:
        print(f'Honda CG 160 Start 2024: R${preco:.0f} (fonte: {fonte})')
    else:
        print('Nao encontrado — usando fallback')
    atualizar_cache_popular()   