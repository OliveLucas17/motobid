#!/usr/bin/env python3
"""
crawlers/ricoleiloes.py — parser Rico Leiloes

Status: em construcao — prioridade antes de 01/06/2026
O leilao Prefeitura Itaoca esta agendado para 09/06/2026.

Layout da Rico Leiloes e diferente do Sumare:
- Modelo sem barra: 'Honda CG 160 Fan'
- Lance no formato: 'Lance minimo: R$ 5.150,00'
- Documento: 'Veiculo com documento'
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
    for i in range(len(linhas)):
        yield '\n'.join(linhas[i:i+tam])

def parse_leilao(html, url_leilao, id_leilao):
    """
    Extrai lotes da Rico Leiloes.
    Formato diferente do Sumare — sem barra no modelo.
    """
    if not html:
        log(f'  [Rico] pagina vazia: {url_leilao}')
        return []

    categoria = detectar_categoria(html)
    log(f'  [Rico] categoria detectada: {categoria}')

    linhas = [l.strip() for l in html.split('\n') if len(l.strip()) > 5]
    lotes  = []
    vistos = set()

    for bloco in janelas(linhas, tam=12):
        marca = detectar_marca(bloco)
        if not marca:
            continue

        # Rico nao usa barra — modelo vem direto
        modelo_raw = None
        m = re.search(
            rf'({marca})\s+([A-Z0-9\s\-]{{3,40}}?)\s+\d{{2}}/\d{{2}}',
            bloco.upper()
        )
        if m:
            modelo_raw = f'{m.group(1)} {m.group(2)}'.strip()

        modelo  = normalizar_modelo(modelo_raw) if modelo_raw else marca
        ano_str, ano_int = extrair_ano(bloco)
        lance   = extrair_preco(bloco)
        cor     = extrair_cor(bloco)
        tem_doc = doc_ok(bloco)

        lote_id = extrair_lote_id(bloco, url_leilao)
        if not lote_id:
            lote_id = f'RICO-{id_leilao}-{abs(hash(bloco[:60])) % 9999:04d}'

        if lote_id in vistos:
            continue
        vistos.add(lote_id)

        if not tem_doc:
            log(f'    REJEITADO {lote_id} — sem documento')
            continue

        if ano_int and not ano_valido(ano_int):
            log(f'    REJEITADO {lote_id} — ano {ano_int}')
            continue

        if not lance or lance < LANCE_MINIMO or lance > LANCE_MAXIMO:
            continue

        fipe, fipe_fonte = get_preco_ref(modelo, marca)
        if not fipe:
            fipe, fipe_fonte = 10000, 'fallback_conservador'

        tier  = get_tier(marca)
        score = calcular_score(tier, fipe, lance, tem_doc, ano_int)
        ok, motivo = aprovado(
            tier, fipe, lance, tem_doc,
            ano_int, score, categoria, bloco
        )

        if not ok:
            log(f'    REJEITADO {lote_id} ({modelo}): {motivo}')
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
            'site':            'ricoleiloes',
            'url_lote':        url_leilao,
            'status':          'ativo',
            'fase':            'pre_leilao',
        }
        lotes.append(lote)
        log(f'    OK {lote_id} | {modelo} {ano_str} | '
            f'lance R${lance:.0f} | margem R${margem:.0f} | score {score}')

    log(f'  [Rico] {len(lotes)} lote(s) aprovado(s)')
    return lotes