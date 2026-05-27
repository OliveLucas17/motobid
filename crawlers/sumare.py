#!/usr/bin/env python3
"""
crawlers/sumare.py — parser Sumare Leiloes v2.3

Formato real do Sumare apos gsk crawl:
  MARCA/MODELO, ANO/ANO
  CIDADE / SP
  LOTE XXXX DOCUMENTO
  [](https://www.sumareleiloes.com.br/lotes/uuid)
"""
import re
from utils import (
    log, normalizar_modelo, detectar_marca,
    extrair_ano, extrair_preco, extrair_cor, ano_valido
)
from scoring import get_tier, get_preco_ref, calcular_score, aprovado
from config import detectar_categoria, LANCE_MINIMO, LANCE_MAXIMO

# Regex para extrair URL do formato [](url)
RE_URL   = re.compile(r'\[\]\((https://www\.sumareleiloes\.com\.br/lotes/[^\)]+)\)')
RE_LOTE  = re.compile(r'LOTE\s+(\d{3,5})\s+(DOCUMENTO|SUCATA|COM\s+DIREITO)', re.I)
RE_SUCATA = re.compile(r'SUCATA|MOTOR\s+INSERVIVEL|SEM\s+DOCUMENTO', re.I)

def parse_bloco(bloco):
    """
    Parseia um bloco de 4-6 linhas correspondente a um lote.

    Formato esperado:
      MARCA/MODELO, ANO/ANO
      CIDADE / SP
      LOTE XXXX DOCUMENTO
      [](url)
    """
    linhas = [l.strip() for l in bloco.split('\n') if l.strip()]
    if len(linhas) < 3:
        return None

    texto = '\n'.join(linhas)

    # Documento — linha com LOTE
    m_lote = RE_LOTE.search(texto)
    if not m_lote:
        return None

    lote_num  = m_lote.group(1)
    tipo_doc  = m_lote.group(2).upper()
    tem_doc   = 'DOCUMENTO' in tipo_doc or 'DIREITO' in tipo_doc

    # Rejeita sucata imediatamente
    if RE_SUCATA.search(texto):
        return None

    # URL do lote
    m_url = RE_URL.search(texto)
    url   = m_url.group(1) if m_url else ''

    # Modelo e marca — primeira linha geralmente
    modelo_raw = linhas[0]
    marca      = detectar_marca(modelo_raw)
    if not marca:
        return None

    modelo = normalizar_modelo(modelo_raw)

    # Ano
    ano_str, ano_int = extrair_ano(texto)

    # Cor (nem sempre presente na lista)
    cor = extrair_cor(texto)

    return {
        'lote_num': lote_num,
        'modelo':   modelo,
        'marca':    marca,
        'ano_str':  ano_str or '??/??',
        'ano_int':  ano_int,
        'cor':      cor,
        'doc_ok':   tem_doc,
        'url':      url,
    }

def dividir_em_blocos(texto):
    """
    Divide o texto em blocos por lote.
    Cada bloco começa quando detectamos uma marca conhecida.
    """
    linhas  = texto.split('\n')
    blocos  = []
    atual   = []

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        # Nova marca = novo lote
        if detectar_marca(linha) and RE_URL.search('\n'.join(atual)) or (detectar_marca(linha) and len(atual) > 3):
            if atual:
                blocos.append('\n'.join(atual))
            atual = [linha]
        else:
            atual.append(linha)

    if atual:
        blocos.append('\n'.join(atual))

    return blocos

def parse_leilao(html, url_leilao, id_leilao):
    """
    Extrai lotes aprovados da pagina de leilao do Sumare.
    """
    # Extrai conteudo do JSON do gsk
    import json as _json
    conteudo = html
    try:
        data     = _json.loads(html)
        conteudo = data.get('data', {}).get('result', html)
    except:
        pass

    # Remove imagens markdown
    conteudo = re.sub(r'!\[.*?\]\(.*?\)', '', conteudo)
    conteudo = re.sub(r'\n{3,}', '\n\n', conteudo).strip()

    categoria = detectar_categoria(conteudo)
    log(f'  Categoria: {categoria} | Chars: {len(conteudo)}')

    # Divide em blocos por lote
    blocos = dividir_em_blocos(conteudo)
    log(f'  Blocos encontrados: {len(blocos)}')

    lotes   = []
    vistos  = set()
    rejeitados = 0

    for bloco in blocos:
        dados = parse_bloco(bloco)
        if not dados:
            continue

        lote_id = f'{id_leilao}-{dados["lote_num"]}'

        if lote_id in vistos:
            continue
        vistos.add(lote_id)

        if not dados['doc_ok']:
            log(f'    REJEITADO {lote_id} — sem documento')
            rejeitados += 1
            continue

        ano_int = dados['ano_int']
        if ano_int and not ano_valido(ano_int):
            log(f'    REJEITADO {lote_id} — ano {ano_int}')
            rejeitados += 1
            continue

        # Preco — nao aparece na lista, usa FIPE como referencia
        # Lance sera atualizado quando o monitor crawlar o lote individual
        fipe, fipe_fonte = get_preco_ref(dados['modelo'], dados['marca'])
        if not fipe:
            fipe, fipe_fonte = 10000, 'fallback'

        # Lance inicial estimado: 35% do FIPE (media dos leiloes de prefeitura)
        lance_est = round(fipe * 0.35, -2)

        tier  = get_tier(dados['marca'])
        score = calcular_score(tier, fipe, lance_est, True, ano_int)
        ok, motivo = aprovado(
            tier, fipe, lance_est, True,
            ano_int, score, categoria, bloco
        )

        if not ok:
            log(f'    REJEITADO {lote_id} ({dados["modelo"]}): {motivo}')
            rejeitados += 1
            continue

        margem = fipe - lance_est
        lote = {
            'id':              lote_id,
            'modelo':          dados['modelo'],
            'marca':           dados['marca'],
            'ano':             dados['ano_str'],
            'cor':             dados['cor'],
            'tier':            tier,
            'doc_ok':          True,
            'lance_inicial':   lance_est,
            'lance_atual':     lance_est,
            'fipe':            fipe,
            'fipe_fonte':      fipe_fonte,
            'margem_estimada': round(margem, 2),
            'score':           score,
            'leilao':          id_leilao,
            'categoria':       categoria,
            'site':            'sumare',
            'url_lote':        dados['url'] or url_leilao,
            'status':          'ativo',
            'fase':            'pre_leilao',
        }
        lotes.append(lote)
        log(f'    OK {lote_id} | {dados["modelo"]} {dados["ano_str"]} | '
            f'lance est. R${lance_est:.0f} | margem R${margem:.0f} | score {score}')

    log(f'  Resultado: {len(lotes)} aprovados / {len(blocos)} blocos / {rejeitados} rejeitados')
    return lotes