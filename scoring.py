#!/usr/bin/env python3
"""scoring.py — calculo de tier, score e aprovacao."""
from config import (
    TIER_TOP, TIER_ALTA, TIER_OUTRAS, EXCLUIDAS,
    MARGEM_MIN, PRECOS_REF, PRECO_FALLBACK, SCORE_PESOS,
    ANO_MINIMO, LANCE_MINIMO, LANCE_MAXIMO, SCORE_MINIMO,
    SINISTRO_ACEITO, SINISTRO_REJEITADO,
)

def get_tier(marca):
    """Retorna TOP, ALTA, OUTRAS ou None se excluida."""
    m = marca.upper().strip()
    if m in EXCLUIDAS:  return None
    if m in TIER_TOP:   return 'TOP'
    if m in TIER_ALTA:  return 'ALTA'
    if m in TIER_OUTRAS: return 'OUTRAS'
    return None

def get_preco_ref(modelo, marca):
    """Busca preco de referencia. Tenta FIPE API primeiro, fallback tabela."""
    try:
        from fipe import get_preco
        preco, fonte = get_preco(modelo, marca)
        if preco:
            return preco, fonte
    except Exception:
        pass

    # Fallback tabela estatica
    mu = modelo.upper().strip()
    if mu in PRECOS_REF:
        return PRECOS_REF[mu], 'tabela_exata'
    for chave, preco in PRECOS_REF.items():
        if chave in mu or mu in chave:
            return preco, 'tabela_parcial'
    mrc = marca.upper().strip()
    if mrc in PRECO_FALLBACK:
        return PRECO_FALLBACK[mrc], 'fallback_marca'
    return None, None

def calcular_score(tier, fipe, lance, doc_ok, ano_int):
    """Calcula score de 0.0 a 10.0."""
    if tier is None:
        return 0.0
    p    = SCORE_PESOS
    base = p['tier_top'] if tier=='TOP' else p['tier_alta'] if tier=='ALTA' else p['tier_outras']
    doc_b  = p['doc_ok'] if doc_ok else 0
    margem = fipe - lance if fipe else 0
    pct    = margem / fipe if fipe > 0 else 0
    mg_b   = min(p['margem_bonus'], round(pct * p['margem_bonus'] / 0.4, 1))
    ano_b  = 0
    if ano_int:
        if ano_int >= 2020:   ano_b = p['ano_2020']
        elif ano_int >= 2015: ano_b = p['ano_2015']
    return round(min(10.0, base + doc_b + mg_b + ano_b), 1)

def validar_sinistro(texto, categoria):
    """Para lotes de sinistro, verifica se a classificacao e aceita."""
    if categoria != 'sinistro':
        return True, None
    tl = texto.lower()
    for rejeitado in SINISTRO_REJEITADO:
        if rejeitado in tl:
            return False, f'sinistro rejeitado: {rejeitado}'
    for aceito in SINISTRO_ACEITO:
        if aceito in tl:
            return True, aceito
    return False, 'classificacao de sinistro nao identificada'

def aprovado(tier, fipe, lance, doc_ok, ano_int, score, categoria='prefeitura', texto=''):
    """Retorna (True, motivo) ou (False, motivo)."""
    # 1. Documento — regra absoluta
    if not doc_ok:
        return False, 'SEM DOCUMENTO — reprovado'

    # 2. Marca
    if tier is None:
        return False, 'marca desconhecida ou excluida'

    # 3. Ano
    if ano_int and ano_int < ANO_MINIMO:
        return False, f'ano {ano_int} < minimo ({ANO_MINIMO})'

    # 4. Lance
    if not lance or lance < LANCE_MINIMO:
        return False, f'lance R${lance} abaixo do minimo'
    if lance > LANCE_MAXIMO:
        return False, f'lance R${lance} acima do maximo'

    # 5. Sinistro — classificacao
    sin_ok, sin_motivo = validar_sinistro(texto, categoria)
    if not sin_ok:
        return False, sin_motivo

    # 6. Margem
    margem     = (fipe - lance) if fipe else 0
    margem_min = MARGEM_MIN.get(categoria, {}).get(tier, 9999)
    if margem < margem_min:
        return False, f'margem R${margem:.0f} < minimo R${margem_min} ({tier}/{categoria})'

    # 7. Score
    if score < SCORE_MINIMO:
        return False, f'score {score} < minimo ({SCORE_MINIMO})'

    return True, 'aprovado'
    