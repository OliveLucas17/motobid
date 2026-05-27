#!/usr/bin/env python3
"""
auto_scout.py — MotoBid v2.1
Varredura automatica de todas as plataformas.
Roda 1x por dia via cron (07:00).

Fluxo:
  1. Varre todas as plataformas de PLATAFORMAS_SP
  2. Para cada plataforma, busca leiloes ativos de motos
  3. Para cada leilao, extrai lotes e aplica filtros
  4. Lotes aprovados vao para state.json
  5. Envia alertas por email e Telegram
"""
import re, os, json, time, subprocess, smtplib
from datetime import datetime
from email.mime.text import MIMEText

from config import (
    PLATAFORMAS_SP, LEILOES_SUMARE, LEILOES_RICO,
    URL_SUMARE_LEILAO, EMAIL_TO,
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
)
from crawlers import crawl_url
from crawlers.sumare import parse_leilao as parse_sumare
from crawlers.ricoleiloes import parse_leilao as parse_rico
from utils import log, carregar_json, salvar_json

STATE_FILE = 'data/state.json'
LOG_FILE   = 'data/scout.log'

def logf(msg):
    log(msg, LOG_FILE)

# ─────────────────────────────────────────────────────────
# NOTIFICACOES
# ─────────────────────────────────────────────────────────
def enviar_email(assunto, corpo):
    try:
        msg = MIMEText(corpo, 'plain', 'utf-8')
        msg['Subject'] = assunto
        msg['From']    = 'motobid@localhost'
        msg['To']      = EMAIL_TO
        with smtplib.SMTP('localhost', 25, timeout=10) as s:
            s.sendmail('motobid@localhost', [EMAIL_TO], msg.as_string())
        logf('  email enviado')
    except Exception as e:
        logf(f'  email erro: {e}')

def enviar_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import urllib.request, urllib.parse
        url  = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        data = urllib.parse.urlencode({
            'chat_id':    TELEGRAM_CHAT_ID,
            'text':       msg,
            'parse_mode': 'HTML',
        }).encode()
        urllib.request.urlopen(url, data, timeout=10)
        logf('  telegram enviado')
    except Exception as e:
        logf(f'  telegram erro: {e}')

def notificar_novo(lote):
    modelo = lote.get('modelo', '?')
    ano    = lote.get('ano', '')
    lance  = lote.get('lance_atual', 0)
    margem = lote.get('margem_estimada', 0)
    score  = lote.get('score', 0)
    cat    = lote.get('categoria', '?').upper()
    url    = lote.get('url_lote', '')
    msg = (
        f'[{cat}] Novo lote encontrado\n'
        f'{modelo} {ano}\n'
        f'Lance: R${lance:,.0f} | Margem: R${margem:,.0f} | Score: {score}\n'
        f'{url}'
    )
    enviar_email(f'[MotoBid] {modelo} | R${margem:,.0f} margem', msg)
    enviar_telegram(msg)

# ─────────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────────
def add_lote(state, lote):
    """Adiciona lote se nao existir. Retorna True se novo."""
    lid = lote['id']
    if lid in state:
        return False
    lote['added_at']   = datetime.now().isoformat()
    lote['last_check'] = None
    state[lid] = lote
    return True

# ─────────────────────────────────────────────────────────
# BUSCA DE LEILOES ATIVOS
# ─────────────────────────────────────────────────────────
def buscar_urls_leilao(url_base, slug):
    """
    Usa gsk search para encontrar leiloes de motos
    dentro de uma plataforma.
    Retorna lista de URLs de leiloes encontrados.
    """
    urls = []
    query = f'site:{url_base.replace("https://","").replace("http://","").rstrip("/")} moto leilao'
    try:
        r = subprocess.run(
            ['gsk', 'search', query],
            capture_output=True, text=True, timeout=30
        )
        # Extrai URLs do resultado
        encontradas = re.findall(
            rf'https?://{re.escape(url_base.replace("https://","").replace("http://","").rstrip("/"))}[^\s"\'<>]+',
            r.stdout
        )
        # Filtra URLs que parecem ser de leilao
        for u in encontradas:
            if any(p in u.lower() for p in ['/leilao', '/lote', '/veiculo', '/moto', '/bem']):
                if u not in urls:
                    urls.append(u)
        logf(f'  {slug}: {len(urls)} URL(s) encontrada(s) via search')
    except Exception as e:
        logf(f'  {slug} search erro: {e}')
    return urls[:10]  # maximo 10 por plataforma por rodada

def escolher_parser(slug):
    """Retorna a funcao de parse correta para cada plataforma."""
    if 'sumare' in slug:
        return parse_sumare
    if 'rico' in slug:
        return parse_rico
    # Default: tenta o parser do Sumare (mais robusto)
    return parse_sumare

# ─────────────────────────────────────────────────────────
# VARREDURA SUMARE — lista fixa de IDs conhecidos
# ─────────────────────────────────────────────────────────
def scout_sumare(state):
    logf('--- Sumare Leiloes (IDs conhecidos) ---')
    total = 0

    # IDs conhecidos + busca por novos
    todos = dict(LEILOES_SUMARE)
    try:
        r = subprocess.run(
            ['gsk', 'search', 'site:sumareleiloes.com.br leilao motos'],
            capture_output=True, text=True, timeout=30
        )
        novos_ids = re.findall(r'/leiloes/(\d{3,6})', r.stdout)
        for nid in novos_ids:
            if nid not in todos:
                todos[nid] = 'descoberto via search'
                logf(f'  Novo ID descoberto: {nid}')
    except Exception as e:
        logf(f'  search erro: {e}')

    for lid, desc in todos.items():
        url  = URL_SUMARE_LEILAO.format(id=lid)
        logf(f'  Leilao {lid} ({desc}): {url}')
        html = crawl_url(url, render_js=True)
        if not html:
            logf(f'  Sem resposta — pulando')
            continue
        lotes = parse_sumare(html, url, lid)
        for l in lotes:
            if add_lote(state, l):
                total += 1
                notificar_novo(l)
        time.sleep(2)  # respeita o servidor

    logf(f'  Sumare: {total} lote(s) novo(s)')
    return total

# ─────────────────────────────────────────────────────────
# VARREDURA RICO LEILOES
# ─────────────────────────────────────────────────────────
def scout_rico(state):
    logf('--- Rico Leiloes ---')
    total = 0
    for lid, info in LEILOES_RICO.items():
        url  = info['url']
        logf(f'  Leilao {lid} ({info["nome"]}): {url}')
        html = crawl_url(url, render_js=True)
        if not html:
            logf(f'  Sem resposta — pulando')
            continue
        lotes = parse_rico(html, url, lid)
        for l in lotes:
            if add_lote(state, l):
                total += 1
                notificar_novo(l)
        time.sleep(2)
    logf(f'  Rico: {total} lote(s) novo(s)')
    return total

# ─────────────────────────────────────────────────────────
# VARREDURA TODAS AS PLATAFORMAS
# ─────────────────────────────────────────────────────────
def scout_plataformas(state):
    """
    Varre todas as 34 plataformas de PLATAFORMAS_SP.
    Para cada uma, usa gsk search para encontrar leiloes
    de motos ativos e extrai os lotes.
    """
    logf('--- Varredura geral (34 plataformas) ---')
    total = 0

    # Pula Sumare e Rico — ja varridos com logica propria
    pular = {'sumareleiloes', 'ricoleiloes'}

    ativos = {
        slug: info
        for slug, info in PLATAFORMAS_SP.items()
        if info.get('ativo') and slug not in pular
    }

    logf(f'  {len(ativos)} plataformas para varrer')

    for slug, info in ativos.items():
        url_base = info['url']
        leiloeiro = info['leiloeiro']
        logf(f'  [{slug}] {leiloeiro}: {url_base}')

        urls = buscar_urls_leilao(url_base, slug)
        if not urls:
            # Tenta crawl direto na home
            urls = [url_base]

        parser = escolher_parser(slug)

        for url in urls:
            html = crawl_url(url, render_js=True)
            if not html:
                continue
            try:
                lotes = parser(html, url, slug)
                for l in lotes:
                    l['site'] = slug  # marca a origem
                    if add_lote(state, l):
                        total += 1
                        notificar_novo(l)
            except Exception as e:
                logf(f'    parse erro em {url}: {e}')
            time.sleep(3)  # respeita o servidor

    logf(f'  Plataformas: {total} lote(s) novo(s)')
    return total

# ─────────────────────────────────────────────────────────
# ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────
def scout_all():
    logf('=' * 50)
    logf('MOTOBID SCOUT — inicio')
    logf(f'Data/hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
    logf('=' * 50)

    os.makedirs('data', exist_ok=True)
    state = carregar_json(STATE_FILE, {})
    antes = len(state)

    # 1. Sumare — IDs conhecidos (mais confiavel)
    scout_sumare(state)

    # 2. Rico Leiloes — leiloes agendados
    scout_rico(state)

    # 3. Todas as outras plataformas
    scout_plataformas(state)

    # Salva estado atualizado
    salvar_json(STATE_FILE, state)

    depois  = len(state)
    novos   = depois - antes
    logf('=' * 50)
    logf(f'FIM — {novos} lote(s) novo(s) | {depois} total no sistema')
    logf('=' * 50)

    # Resumo por email
    if novos > 0:
        resumo = '\n'.join(
            f'- {l["modelo"]} {l["ano"]} | R${l["lance_atual"]:,.0f} | '
            f'margem R${l["margem_estimada"]:,.0f} | score {l["score"]}'
            for lid, l in state.items()
            if l.get('added_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))
        )
        enviar_email(
            f'[MotoBid] Scout: {novos} lote(s) novo(s)',
            f'Novos lotes encontrados hoje:\n\n{resumo}'
        )

if __name__ == '__main__':
    scout_all()