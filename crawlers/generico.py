#!/usr/bin/env python3
"""
crawlers/generico.py — Parser generico para qualquer plataforma

Funciona com qualquer site de leilao que o gsk consiga crawlar.
Mais flexivel que o parser do Sumare — aceita formatos variados.

Logica:
  1. Extrai texto do JSON do gsk
  2. Verifica se o leilao esta ativo (data de fechamento)
  3. Detecta categoria automaticamente (prefeitura/financeira/sinistro)
  4. Varre o texto procurando blocos com marca + ano + documento
  5. Aplica filtros e scoring
"""
import re, json as _json
from datetime import datetime
from utils import (
    log, normalizar_modelo, detectar_marca,
    extrair_ano, extrair_preco, extrair_cor, ano_valido
)
from scoring import get_tier, get_preco_ref, calcular_score, aprovado
from config import (
    detectar_categoria, LANCE_MINIMO, LANCE_MAXIMO,
    MODELOS_CARRO, SUCATA_KEYWORDS, DOC_OK_KEYWORDS
)

# ── Meses em portugues ─────────────────────────────────────
MESES = {
    'janeiro':1,'fevereiro':2,'marco':3,'março':3,'abril':4,
    'maio':5,'junho':6,'julho':7,'agosto':8,'setembro':9,
    'outubro':10,'novembro':11,'dezembro':12,
    'jan':1,'fev':2,'mar':3,'abr':4,'mai':5,'jun':6,
    'jul':7,'ago':8,'set':9,'out':10,'nov':11,'dez':12,
}

# ── Extrator de conteudo gsk ───────────────────────────────
def extrair_conteudo(html):
    """Extrai texto util do JSON retornado pelo gsk crawl."""
    try:
        data     = _json.loads(html)
        conteudo = data.get('data', {}).get('result', html)
    except:
        conteudo = html

    # Remove imagens markdown
    conteudo = re.sub(r'!\[.*?\]\(.*?\)', '', conteudo)
    conteudo = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', conteudo)
    conteudo = re.sub(r'\n{3,}', '\n\n', conteudo).strip()
    return conteudo

# ── Filtro de data ─────────────────────────────────────────
def extrair_datas(texto):
    """Extrai datas de abertura e fechamento do texto."""
    datas = {}

    # Formato DD/MM/AAAA
    for label, chave in [
        (r'[Ff]echamento', 'fechamento'),
        (r'[Ee]ncerramento', 'fechamento'),
        (r'[Aa]bertura', 'abertura'),
        (r'[Ii]n[ií]cio', 'abertura'),
    ]:
        # DD/MM/AAAA
        m = re.search(rf'{label}[:\s]+(\d{{1,2}})/(\d{{1,2}})/(\d{{4}})', texto)
        if m:
            try:
                datas[chave] = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                continue
            except:
                pass
        # DD de mes de AAAA
        m = re.search(
            rf'{label}[:\s]+\w*,?\s*(\d{{1,2}})\s+(?:de\s+)?(\w+)\s+(?:de\s+)?(\d{{4}})',
            texto, re.I
        )
        if m:
            try:
                dia = int(m.group(1))
                mes = MESES.get(m.group(2).lower().replace('ç','c'), 0)
                ano = int(m.group(3))
                if mes:
                    datas[chave] = datetime(ano, mes, dia)
            except:
                pass

    return datas

def leilao_ativo(conteudo, slug=''):
    """
    Verifica se o leilao ainda esta ativo.
    Retorna True se ativo ou se nao conseguir determinar.
    """
    # Palavras que indicam encerramento explicito
    tl = conteudo.lower()
    if any(k in tl for k in [
        'leilão encerrado', 'leilao encerrado',
        'encerrado', 'finalizado', 'arrematado',
        'leilão realizado', 'leilao realizado',
    ]):
        # Verifica se e um texto geral do site ou do leilao especifico
        # Se aparecer mais de 3x, provavelmente e do leilao
        count = tl.count('encerrado')
        if count >= 2:
            log(f'  [{slug}] Leilao parece encerrado (keyword x{count})')
            return False

    # Verifica pela data de fechamento
    datas = extrair_datas(conteudo)
    if 'fechamento' in datas:
        data_fech = datas['fechamento']
        if data_fech < datetime.now():
            log(f'  [{slug}] Leilao encerrado em {data_fech.strftime("%d/%m/%Y")}')
            return False
        else:
            log(f'  [{slug}] Leilao ativo ate {data_fech.strftime("%d/%m/%Y")}')

    return True

# ── Verificacao de documento ───────────────────────────────
def tem_documento(texto):
    tl = texto.lower()
    if any(k in tl for k in SUCATA_KEYWORDS):
        return False
    return any(k in tl for k in DOC_OK_KEYWORDS)

# ── Classificacao de carro ─────────────────────────────────
def eh_carro(modelo):
    mu = modelo.upper()
    return any(c in mu for c in MODELOS_CARRO)

# ── Janela deslizante generica ─────────────────────────────
def janelas(linhas, tam=15):
    for i in range(len(linhas)):
        yield i, '\n'.join(linhas[i:i+tam])

# ── Parser principal ───────────────────────────────────────
def parse_leilao(html, url_leilao, slug):
    conteudo = extrair_conteudo(html)
    log(f'  [{slug}] Chars: {len(conteudo)}')

    # ← ADICIONA AQUI — conteudo insuficiente
    if len(conteudo) < 300:
        log(f'  [{slug}] Conteudo insuficiente — pulando')
        return []

    # Verifica se o leilao esta ativo
    if not leilao_ativo(conteudo, slug):
        return []

    # ← ADICIONA AQUI — detecta categoria
    categoria = detectar_categoria(conteudo)
    if categoria is None:
        log(f'  [{slug}] Categoria nao detectada — varredura geral')
        categoria = 'prefeitura'  # fallback neutro

    log(f'  [{slug}] Categoria: {categoria}')

    # ... resto do codigo continua igual
    # Verifica se o leilao esta ativo
    if not leilao_ativo(conteudo, slug):
        return []

    # Detecta categoria
    categoria = detectar_categoria(conteudo)
    log(f'  [{slug}] Categoria: {categoria}')

    # Verifica sinistro — classifica tipo de dano
    sinistro_tipo = None
    if categoria == 'sinistro':
        tl = conteudo.lower()
        for tipo in ['pequena monta', 'media monta', 'perda total', 'colisao']:
            if tipo in tl:
                sinistro_tipo = tipo
                break
        # Rejeita sinistros nao aceitos
        from config import SINISTRO_ACEITO
        if sinistro_tipo and sinistro_tipo not in SINISTRO_ACEITO:
            log(f'  [{slug}] Sinistro rejeitado: {sinistro_tipo}')
            return []

    linhas = [l.strip() for l in conteudo.split('\n') if len(l.strip()) > 3]
    lotes     = []
    vistos    = set()
    rejeitados = 0

    for idx, bloco in janelas(linhas, tam=15):
        marca = detectar_marca(bloco)
        if not marca:
            continue

        modelo_raw = None
        # Tenta extrair modelo da linha onde a marca aparece
        for linha in bloco.split('\n')[:5]:
            if detectar_marca(linha):
                modelo_raw = linha
                break
        if not modelo_raw:
            continue

        modelo  = normalizar_modelo(modelo_raw)
        ano_str, ano_int = extrair_ano(bloco)
        lance   = extrair_preco(bloco)
        cor     = extrair_cor(bloco)
        doc     = tem_documento(bloco)

        # ID unico baseado em posicao + modelo
        lote_id = f'{slug}-{abs(hash(modelo + str(ano_str) + str(lance))) % 99999:05d}'

        if lote_id in vistos:
            continue
        vistos.add(lote_id)

        # Categoriza carros na section futura
        categoria_final = 'carros' if eh_carro(modelo) else categoria

        # Validacao de documento
        if not doc and categoria_final != 'carros':
            rejeitados += 1
            continue

        # Validacao de ano
        if ano_int and not ano_valido(ano_int):
            log(f'    REJEITADO {lote_id} — ano {ano_int}')
            rejeitados += 1
            continue

        # Lance — se nao encontrou usa estimativa
        fipe, fipe_fonte = get_preco_ref(modelo, marca)
        if not fipe:
            fipe, fipe_fonte = 10000, 'fallback'

        lance_final = lance if lance and LANCE_MINIMO <= lance <= LANCE_MAXIMO else round(fipe * 0.35, -2)

        tier  = get_tier(marca)
        score = calcular_score(tier, fipe, lance_final, doc, ano_int)
        ok, motivo = aprovado(
            tier, fipe, lance_final, doc,
            ano_int, score, categoria_final, bloco
        )

        if not ok and categoria_final != 'carros':
            log(f'    REJEITADO {lote_id} ({modelo}): {motivo}')
            rejeitados += 1
            continue

        margem = fipe - lance_final
        lote = {
            'id':              lote_id,
            'modelo':          modelo,
            'marca':           marca,
            'ano':             ano_str or '??/??',
            'cor':             cor,
            'tier':            tier,
            'doc_ok':          doc,
            'lance_inicial':   lance_final,
            'lance_atual':     lance_final,
            'fipe':            fipe,
            'fipe_fonte':      fipe_fonte,
            'margem_estimada': round(margem, 2),
            'score':           score,
            'leilao':          slug,
            'categoria':       categoria_final,
            'sinistro_tipo':   sinistro_tipo,
            'site':            slug,
            'url_lote':        url_leilao,
            'status':          'ativo',
            'fase':            'pre_leilao',
        }
        lotes.append(lote)
        log(f'    OK {lote_id} | {modelo} {ano_str} | '
            f'R${lance_final:.0f} | margem R${margem:.0f} | score {score} | {categoria_final}')

    log(f'  [{slug}] Resultado: {len(lotes)} aprovados / {rejeitados} rejeitados')
    return lotes