#!/usr/bin/env python3
"""
crawlers/sumare.py — parser Sumare Leiloes v2.4

Fixes v2.4:
- Filtro de data: leiloes encerrados sao ignorados
- Filtro de carros: modelos de carro rejeitados automaticamente
- Filtro de email spam removido (notificacao agrupada no scout_all)
"""
import re, json as _json
from datetime import datetime
from utils import (
    log, normalizar_modelo, detectar_marca,
    extrair_ano, extrair_cor, ano_valido
)
from scoring import get_tier, get_preco_ref, calcular_score, aprovado
from config import detectar_categoria, LANCE_MINIMO, LANCE_MAXIMO, MODELOS_CARRO

# ── Regex ──────────────────────────────────────────────────
RE_URL   = re.compile(
    r'\[URL_LOTE:(https://www\.sumareleiloes\.com\.br/lotes/[^\]]+)\]'
)
RE_LOTE  = re.compile(
    r'LOTE\s+(\d{3,5})\s*\n\s*(DOCUMENTO|SUCATA|COM\s+DIREITO)',
    re.I
)
RE_SUCATA = re.compile(r'SUCATA|MOTOR\s+INSERVIVEL|SEM\s+DOCUMENTO', re.I)
# ── Meses em portugues ─────────────────────────────────────
MESES = {
    'janeiro':1,'fevereiro':2,'marco':3,'março':3,'abril':4,
    'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,
    'outubro':10,'novembro':11,'dezembro':12
}

# ── Filtro de data ─────────────────────────────────────────
def extrair_data_fechamento(texto):
    """Extrai a data de fechamento do leilao.
    Formato Sumare: 'Fechamento: Terca-feira, 29 maio 2018, 10:00h'
    """
    m = re.search(
        r'[Ff]echamento[:\s]+\w+,?\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
        texto
    )
    if m:
        try:
            dia = int(m.group(1))
            mes = MESES.get(m.group(2).lower().replace('ç','c'), 0)
            ano = int(m.group(3))
            if mes:
                return datetime(ano, mes, dia)
        except:
            pass
    return None

def leilao_ativo(conteudo, id_leilao):
    """Retorna True se o leilao ainda esta aberto."""
    data = extrair_data_fechamento(conteudo)
    if data is None:
        return True  # sem data = assume ativo
    if data < datetime.now():
        log(f'  Leilao {id_leilao} encerrado em {data.strftime("%d/%m/%Y")} — ignorando')
        return False
    log(f'  Leilao {id_leilao} ativo ate {data.strftime("%d/%m/%Y")}')
    return True

# ── Filtro de carros ───────────────────────────────────────
def eh_carro(modelo):
    """Retorna True se o modelo for de carro, nao moto."""
    mu = modelo.upper()
    return any(c in mu for c in MODELOS_CARRO)

is_carro = eh_carro

def extrair_conteudo(html):
    """Extrai texto limpo + preserva URLs dos lotes."""
    # Tenta JSON do gsk (legado)
    try:
        data = _json.loads(html)
        c = data.get('data', {}).get('result', html)
        c = re.sub(r'!\[.*?\]\(.*?\)', '', c)
        c = re.sub(r'\n{3,}', '\n\n', c).strip()
        return c
    except:
        pass

    # HTML do Playwright
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        # Extrai URLs dos lotes ANTES de remover tags
        # Substitui <a href="/lotes/uuid"> por texto com URL
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/lotes/' in href:
                url_completa = href if href.startswith('http') else f'https://www.sumareleiloes.com.br{href}'
                a.replace_with(f'\n[URL_LOTE:{url_completa}]\n')

        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav']):
            tag.decompose()

        texto = soup.get_text(separator='\n', strip=True)
        texto = re.sub(r'\n{3,}', '\n\n', texto).strip()
        return texto
    except:
        pass

    texto = re.sub(r'<[^>]+>', ' ', html)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


# ── Parser de bloco ────────────────────────────────────────
def parse_bloco(bloco):
    """
    Parseia um bloco de linhas correspondente a um lote.

    Formato Sumare:
      HONDA/CG 160 START, 24/24
      VINHEDO / SP
      LOTE 0054 DOCUMENTO
      [](https://www.sumareleiloes.com.br/lotes/uuid)
    """
    linhas = [l.strip() for l in bloco.split('\n') if l.strip()]
    if len(linhas) < 3:
        return None

    texto = '\n'.join(linhas)

    # Precisa ter linha de LOTE
    m_lote = RE_LOTE.search(texto)
    if not m_lote:
        return None

    lote_num = m_lote.group(1)
    tipo_doc = m_lote.group(2).upper()
    tem_doc  = 'DOCUMENTO' in tipo_doc or 'DIREITO' in tipo_doc

    # Rejeita sucata imediatamente
    if RE_SUCATA.search(texto):
        return None

    # URL do lote
    m_url = RE_URL.search(texto)
    url   = m_url.group(1) if m_url else ''

    # Modelo — primeira linha
    modelo_raw = linhas[0]
    marca      = detectar_marca(modelo_raw)
    if not marca:
        return None

    modelo = normalizar_modelo(modelo_raw)

    # Rejeita carros
    if eh_carro(modelo):
        return None

    # Ano e cor
    ano_str, ano_int = extrair_ano(texto)
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
        'is_carro': is_carro
    }

# ── Divisao em blocos ──────────────────────────────────────
def dividir_em_blocos(texto):
    """
    Divide o texto em blocos por lote.
    Novo bloco começa quando detecta nova marca
    depois de ja ter acumulado conteudo.
    """
    linhas = texto.split('\n')
    blocos = []
    atual  = []

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        nova_marca = detectar_marca(linha)
        ja_tem_url = RE_URL.search('\n'.join(atual))
        bloco_grande = len(atual) > 3

        if nova_marca and (ja_tem_url or bloco_grande):
            if atual:
                blocos.append('\n'.join(atual))
            atual = [linha]
        else:
            atual.append(linha)

    if atual:
        blocos.append('\n'.join(atual))

    return blocos

# ── Parser principal ───────────────────────────────────────
def parse_leilao(html, url_leilao, id_leilao):
    """Extrai lotes aprovados de uma pagina de leilao do Sumare."""
    conteudo = extrair_conteudo(html)

    if not leilao_ativo(conteudo, id_leilao):
        return []

    categoria = 'prefeitura'
    log(f'  Categoria: {categoria} | Chars: {len(conteudo)}')

    blocos     = dividir_em_blocos(conteudo)
    log(f'  Blocos encontrados: {len(blocos)}')

    lotes      = []
    vistos     = set()
    rejeitados = 0

    # ... continua com o for loop

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

        # Preco de referencia
        fipe, fipe_fonte = get_preco_ref(dados['modelo'], dados['marca'])
        if not fipe:
            fipe, fipe_fonte = 10000, 'fallback'

        # Lance estimado: 35% do FIPE (media prefeitura)
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
            'categoria':       'prefeitura',
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