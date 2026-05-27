#!/usr/bin/env python3
"""
crawlers/sumare.py — parser Sumare Leiloes

Estrategia:
  - Janela deslizante de linhas (resolve bug de campos separados)
  - Normalizacao de modelo (remove barra do formato Sumare)
  - Deteccao automatica de categoria por texto
  - Validacao rigorosa antes de aprovar
"""
import re
from utils import (
    log, normalizar_modelo, detectar_marca,
    extrair_ano, extrair_preco, extrair_cor,
    extrair_lote_id, doc_ok, ano_valido
)
from scoring import get_tier, get_preco_ref, calcular_score, aprovado
from config import LANCE_MINIMO, LANCE_MAXIMO, detectar_categoria

def janelas(linhas, tam=12):
    """
    Gera janelas deslizantes de N linhas.
    Resolve o bug principal: modelo na linha 3, preco na linha 7.
    Sem janela, cada linha vira um bloco isolado e nenhum passa.
    Com janela, capturamos todos os campos de um lote de uma vez.
    """
    for i in range(len(linhas)):
        yield '\n'.join(linhas[i:i+tam])

def extrair_modelo_sumare(bloco, marca):
    """
    Parser especifico para o formato do Sumare:
    'HONDA/CG 160 START 2024/2024'
    'H/HONDA CG 125 TODAY 92/92'
    """
    bloco_up = bloco.upper()

    # Formato principal: MARCA/MODELO ANO
    m = re.search(
        rf'({marca})[/\s]([A-Z0-9\s\-]{{3,40}}?)\s+\d{{2}}/\d{{2}}',
        bloco_up
    )
    if m:
        return normalizar_modelo(f'{m.group(1)} {m.group(2)}')

    # Formato H/HONDA
    m = re.search(r'H/(HONDA)\s+([A-Z0-9\s\-]{3,40})', bloco_up)
    if m:
        return normalizar_modelo(f'{m.group(1)} {m.group(2)}')

    # Fallback: so a marca
    return marca

def parse_leilao(html, url_leilao, id_leilao):
    """
    Extrai todos os lotes aprovados de uma pagina de leilao do Sumare.

    Parametros:
      html        — texto da pagina apos crawl
      url_leilao  — URL de origem (para log e url_lote)
      id_leilao   — ID do leilao (ex: '5105')

    Retorna lista de dicts com dados de cada lote aprovado.
    """
    # Detecta categoria do leilao pelo texto completo
    categoria = detectar_categoria(html)
    log(f'  Categoria detectada: {categoria}')

    linhas = [l.strip() for l in html.split('\n') if len(l.strip()) > 5]
    lotes  = []
    vistos = set()
    total_analisados  = 0
    total_rejeitados  = 0

    for bloco in janelas(linhas, tam=12):
        marca = detectar_marca(bloco)
        if not marca:
            continue

        total_analisados += 1

        # Extrai campos
        modelo  = extrair_modelo_sumare(bloco, marca)
        ano_str, ano_int = extrair_ano(bloco)
        lance   = extrair_preco(bloco)
        cor     = extrair_cor(bloco)
        tem_doc = doc_ok(bloco)

        # ID do lote
        lote_id = extrair_lote_id(bloco, url_leilao)
        if not lote_id:
            lote_id = f'{id_leilao}-{abs(hash(bloco[:60])) % 9999:04d}'

        # Evita duplicatas
        if lote_id in vistos:
            continue
        vistos.add(lote_id)

        # Validacoes em ordem de custo computacional
        # (mais barato primeiro — falha rapido)
        if not tem_doc:
            log(f'    REJEITADO {lote_id} — sem documento')
            total_rejeitados += 1
            continue

        if ano_int and not ano_valido(ano_int):
            log(f'    REJEITADO {lote_id} — ano {ano_int}')
            total_rejeitados += 1
            continue

        if not lance or lance < LANCE_MINIMO or lance > LANCE_MAXIMO:
            total_rejeitados += 1
            continue

        # Preco de referencia (FIPE API ou tabela)
        fipe, fipe_fonte = get_preco_ref(modelo, marca)
        if not fipe:
            log(f'    SEM PRECO_REF: {modelo} — usando fallback conservador')
            fipe, fipe_fonte = 10000, 'fallback_conservador'

        # Tier e score
        tier  = get_tier(marca)
        score = calcular_score(tier, fipe, lance, tem_doc, ano_int)

        # Aprovacao final
        ok, motivo = aprovado(
            tier, fipe, lance, tem_doc,
            ano_int, score, categoria, bloco
        )

        if not ok:
            log(f'    REJEITADO {lote_id} ({modelo}): {motivo}')
            total_rejeitados += 1
            continue

        margem = fipe - lance
        lote = {
            'id':              lote_id,
            'modelo':          modelo,
            'marca':           marca,
            'ano':             ano_str or '??/??',
            'cor':             cor,
            'tier':            tier,
            'doc_ok':          True,
            'lance_inicial':   lance,
            'lance_atual':     lance,
            'fipe':            fipe,
            'fipe_fonte':      fipe_fonte,
            'margem_estimada': round(margem, 2),
            'score':           score,
            'leilao':          id_leilao,
            'categoria':       categoria,
            'site':            'sumare',
            'url_lote':        url_leilao,
            'status':          'ativo',
            'fase':            'pre_leilao',
        }
        lotes.append(lote)
        log(f'    OK {lote_id} | {modelo} {ano_str} | '
            f'lance R${lance:.0f} | margem R${margem:.0f} | score {score}')

    log(f'  Resultado: {len(lotes)} aprovados / '
        f'{total_analisados} analisados / {total_rejeitados} rejeitados')
    return lotes