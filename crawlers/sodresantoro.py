#!/usr/bin/env python3
"""
crawlers/sodresantoro.py — Parser Sodre Santoro
URL de lotes: https://www.sodresantoro.com.br/veiculos/lotes

Formato do lote:
  Leilao XXXXX - XXXX NUM
  modelo marca ano/ano
  BANCO, SEGURADORAS, ETC
  DD/MM/AA HH:MM
  [Hoje]
  Lance atual (R$) - x*x
  VALOR
  * seguro/prefeitura
  * pequena monta / media monta / perda total
  * cidade / SP
  * KM ou -
"""
import re, json as _json
from datetime import datetime
from utils import (
    log, normalizar_modelo, detectar_marca,
    extrair_ano, extrair_cor, ano_valido
)
from scoring import get_tier, get_preco_ref, calcular_score, aprovado
from config import (
    SINISTRO_ACEITO, SINISTRO_REJEITADO,
    MODELOS_CARRO, LANCE_MINIMO, LANCE_MAXIMO
)

URL_LOTES = 'https://www.sodresantoro.com.br/veiculos/lotes'

RE_LEILAO = re.compile(
    r'Leil[aã]o\s+(\d+)\s*-\s*(\d+)',
    re.I
)
RE_LANCE = re.compile(r'Lance\s+atual.*?\n\s*([\d.,]+)', re.I | re.S)
RE_DATA  = re.compile(r'(\d{2})/(\d{2})/(\d{2,4})\s+\d{2}:\d{2}')

def extrair_conteudo(html):
    try:
        data = _json.loads(html)
        c    = data.get('data', {}).get('result', html)
    except:
        c = html
    c = re.sub(r'!\[.*?\]\(.*?\)', '', c)
    c = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', c)
    c = re.sub(r'\n{3,}', '\n\n', c).strip()
    return c

def dividir_lotes(conteudo):
    """Divide o conteudo em blocos por lote usando 'Leilao XXXXX - XXXX'."""
    partes = RE_LEILAO.split(conteudo)
    lotes  = []
    # partes = [texto_antes, id_leilao, id_lote, texto_lote, ...]
    i = 1
    while i < len(partes) - 2:
        id_leilao = partes[i].strip()
        id_lote   = partes[i+1].strip()
        texto     = partes[i+2] if i+2 < len(partes) else ''
        lotes.append((id_leilao, id_lote, texto))
        i += 3
    return lotes

def detectar_tipo_sinistro(texto):
    """Detecta o tipo de sinistro no bloco do lote."""
    tl = texto.lower()
    for tipo in ['pequena monta', 'media monta', 'média monta',
                 'perda total', 'colisao', 'colisão']:
        if tipo in tl:
            return tipo.replace('á','a').replace('ã','a').replace('ç','c')
    return None

def detectar_categoria_lote(texto):
    """Detecta categoria baseado no texto do lote."""
    tl = texto.lower()
    if any(k in tl for k in ['seguro', 'seguradora', 'sinistro',
                               'pequena monta', 'media monta', 'perda total']):
        return 'sinistro'
    if any(k in tl for k in ['banco', 'financeira', 'alienacao',
                               'fiduciaria', 'financiamento']):
        return 'financeira'
    if any(k in tl for k in ['prefeitura', 'detran', 'municipal',
                               'poder publico']):
        return 'prefeitura'
    return 'sinistro'  # sodre santoro e majoritariamente sinistro

def extrair_lance(texto):
    """Extrai o lance atual do bloco."""
    m = RE_LANCE.search(texto)
    if m:
        raw = m.group(1).strip().replace('.','').replace(',','.')
        try:
            return float(raw)
        except:
            pass
    # Tenta encontrar valor isolado
    numeros = re.findall(r'\b(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\b', texto)
    for n in numeros:
        try:
            val = float(n.replace('.','').replace(',','.'))
            if LANCE_MINIMO <= val <= LANCE_MAXIMO:
                return val
        except:
            pass
    return None

def parse_leilao(html, url_leilao, slug='sodresantoro'):
    """Parser especifico para Sodre Santoro."""
    conteudo = extrair_conteudo(html)
    log(f'  [{slug}] Chars: {len(conteudo)}')

    if len(conteudo) < 300:
        log(f'  [{slug}] Conteudo insuficiente — pulando')
        return []

    blocos = dividir_lotes(conteudo)
    log(f'  [{slug}] Lotes encontrados: {len(blocos)}')

    lotes      = []
    vistos     = set()
    rejeitados = 0

    for id_leilao, id_lote, texto in blocos:
        lote_id = f'sodre-{id_leilao}-{id_lote}'

        if lote_id in vistos:
            continue
        vistos.add(lote_id)

        linhas = [l.strip() for l in texto.split('\n') if l.strip()]
        if not linhas:
            continue

        # Linha 0 e numero interno — modelo esta na linha 1
        modelo_raw = linhas[1] if len(linhas) > 1 else linhas[0]
        marca = detectar_marca(modelo_raw)
        if not marca:
            for linha in linhas[:4]:
                if detectar_marca(linha):
                    modelo_raw = linha
                    marca = detectar_marca(linha)
                    break
        if not marca:
            rejeitados += 1
            continue

        modelo = normalizar_modelo(modelo_raw)
        ano_str, ano_int = extrair_ano(texto)
        cor = extrair_cor(texto)
        lance = extrair_lance(texto)

        categoria = detectar_categoria_lote(texto)
        sin_tipo = detectar_tipo_sinistro(texto)

        if any(c in modelo.upper() for c in MODELOS_CARRO):
            categoria = 'carros'

        if categoria == 'sinistro' and sin_tipo:
            sin_norm = sin_tipo.lower()
            aceito = any(a in sin_norm for a in SINISTRO_ACEITO)
            if not aceito:
                log(f'    REJEITADO {lote_id} — sinistro {sin_tipo}')
                rejeitados += 1
                continue
        elif categoria == 'sinistro' and not sin_tipo:
            log(f'    REJEITADO {lote_id} — tipo sinistro nao identificado')
            rejeitados += 1
            continue

        if ano_int and not ano_valido(ano_int):
            log(f'    REJEITADO {lote_id} — ano {ano_int}')
            rejeitados += 1
            continue

        if not lance:
            rejeitados += 1
            continue

        fipe, fipe_fonte = get_preco_ref(modelo, marca)
        if not fipe:
            fipe, fipe_fonte = 10000, 'fallback'

        tier = get_tier(marca)
        doc_ok = True
        score = calcular_score(tier, fipe, lance, doc_ok, ano_int)

        if categoria != 'carros':
            ok, motivo = aprovado(
                tier, fipe, lance, doc_ok,
                ano_int, score, categoria, texto
            )
            if not ok:
                log(f'    REJEITADO {lote_id} ({modelo}): {motivo}')
                rejeitados += 1
                continue

        margem = fipe - lance
        lote = {
            'id':              lote_id,
            'modelo':          modelo,
            'marca':           marca,
            'ano':             ano_str or '??/??',
            'cor':             cor,
            'tier':            tier,
            'doc_ok':          doc_ok,
            'lance_inicial':   lance,
            'lance_atual':     lance,
            'fipe':            fipe,
            'fipe_fonte':      fipe_fonte,
            'margem_estimada': round(margem, 2),
            'score':           score,
            'leilao':          id_leilao,
            'sinistro_tipo':   sin_tipo,
            'categoria':       categoria,
            'site':            'sodresantoro',
            'url_lote':        url_leilao,
            'status':          'ativo',
            'fase':            'pre_leilao',
        }
        lotes.append(lote)
        log(f'    OK {lote_id} | {modelo} {ano_str} | '
            f'R${lance:.0f} | margem R${margem:.0f} | '
            f'{categoria} | {sin_tipo or ""} | score {score}')








