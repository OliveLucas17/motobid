#!/usr/bin/env python3
"""
auto_scout.py — MotoBid v2.1
Varredura automatica de todas as plataformas.
Roda 1x por dia via cron (07:00).
"""
import re, os, json, time, subprocess, smtplib, shutil
from datetime import datetime
from email.mime.text import MIMEText
from crawlers.generico import parse_leilao as parse_generico

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

def enviar_telegram(mensagem):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import urllib.request, urllib.parse
        url  = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        data = urllib.parse.urlencode({
            'chat_id':    TELEGRAM_CHAT_ID,
            'text':       mensagem,
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
    lid = lote['id']
    if lid in state:
        return False
    lote['added_at']   = datetime.now().isoformat()
    lote['last_check'] = None
    state[lid] = lote
    return True

# ─────────────────────────────────────────────────────────
# BUSCA DE LEILOES
# ─────────────────────────────────────────────────────────
def buscar_urls_leilao(url_base, slug):
    urls    = []
    dominio = url_base.replace('https://','').replace('http://','').rstrip('/')

    # Queries especificas por plataforma
    queries_especiais = {
        'superbid':    f'site:{dominio} moto leilao ativo',
        'sodresantoro': f'site:{dominio} moto leilao',
        'lanceleiloes': f'site:{dominio} motocicleta leilao',
        'alienajud':   f'site:{dominio} moto leilao judicial',
        'amaralleiloes': f'site:{dominio} moto leilao',
    }

    query = queries_especiais.get(slug, f'site:{dominio} moto leilao')

    try:
        r = subprocess.run(
            ['gsk', 'search', query],
            capture_output=True, text=True, timeout=30
        )
        encontradas = re.findall(
            rf'https?://{re.escape(dominio)}[^\s"\'<>]+',
            r.stdout
        )
        for u in encontradas:
            if any(p in u.lower() for p in [
                '/leilao', '/lote', '/veiculo', '/moto',
                '/bem', '/produto', '/item', '/catalogo',
                '/busca', '/search',
            ]):
                if u not in urls:
                    urls.append(u)

        logf(f'  {slug}: {len(urls)} URL(s) encontrada(s)')
    except Exception as e:
        logf(f'  {slug} search erro: {e}')

    return urls[:10]

def escolher_parser(slug):
    """Retorna o parser correto para cada plataforma."""
    if 'sumare' in slug:
        return parse_sumare
    if 'rico' in slug:
        return parse_rico
    # Todas as outras plataformas usam o parser generico
    from crawlers.generico import parse_leilao as parse_generico
    return parse_generico
# ─────────────────────────────────────────────────────────
# VARREDURAS
# ─────────────────────────────────────────────────────────
def scout_sumare(state):
    logf('--- Sumare Leiloes ---')
    total = 0
    todos = dict(LEILOES_SUMARE)
    try:
        r = subprocess.run(
            ['gsk', 'search', 'site:sumareleiloes.com.br leilao motos'],
            capture_output=True, text=True, timeout=30
        )
        for nid in re.findall(r'/leiloes/(\d{3,6})', r.stdout):
            if nid not in todos:
                todos[nid] = 'descoberto via search'
                logf(f'  Novo ID: {nid}')
    except Exception as e:
        logf(f'  search erro: {e}')

    for lid, desc in todos.items():
        url = URL_SUMARE_LEILAO.format(id=lid)
        logf(f'  Leilao {lid} ({desc})')
        html = crawl_url(url, render_js=True)
        if not html:
            logf('  Sem resposta — pulando')
            continue
        for l in parse_sumare(html, url, lid):
            if add_lote(state, l):
                total += 1
                notificar_novo(l)
        salvar_json(STATE_FILE, state)
        time.sleep(2)

    logf(f'  Sumare: {total} lote(s) novo(s)')
    return total

def scout_rico(state):
    logf('--- Rico Leiloes ---')
    total = 0
    for lid, info in LEILOES_RICO.items():
        url  = info['url']
        logf(f'  Leilao {lid} ({info["nome"]})')
        html = crawl_url(url, render_js=True)
        if not html:
            logf('  Sem resposta — pulando')
            continue
        for l in parse_rico(html, url, lid):
            if add_lote(state, l):
                total += 1
                notificar_novo(l)
        time.sleep(2)
    logf(f'  Rico: {total} lote(s) novo(s)')
    return total

def scout_plataformas(state):
    logf('--- Varredura geral (34 plataformas) ---')
    total = 0
    pular = {'sumareleiloes', 'ricoleiloes'}
    ativos = {
        slug: info for slug, info in PLATAFORMAS_SP.items()
        if info.get('ativo') and slug not in pular
    }
    logf(f'  {len(ativos)} plataformas para varrer')

    for slug, info in ativos.items():
        url_base  = info['url']
        leiloeiro = info['leiloeiro']
        logf(f'  [{slug}] {leiloeiro}')
        urls = buscar_urls_leilao(url_base, slug) or [url_base]
        parser = escolher_parser(slug)
        for url in urls:
            html = crawl_url(url, render_js=True)
            if not html:
                continue
            try:
                for l in parser(html, url, slug):
                    l['site'] = slug
                    if add_lote(state, l):
                        total += 1
                        notificar_novo(l)
            except Exception as e:
                logf(f'    parse erro: {e}')
            time.sleep(3)

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
    os.makedirs('data/relatorios', exist_ok=True)

    state = carregar_json(STATE_FILE, {})
    antes = len(state)

    scout_sumare(state)
    scout_rico(state)
    scout_plataformas(state)

    salvar_json(STATE_FILE, state)

    depois = len(state)
    novos  = depois - antes

    logf('=' * 50)
    logf(f'FIM — {novos} lote(s) novo(s) | {depois} total no sistema')
    logf('=' * 50)

    # Relatorio diario — salvo APOS o scout terminar
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    relatorio = f'data/relatorios/scout_{data_hoje}.log'
    if os.path.exists(LOG_FILE):
        shutil.copy(LOG_FILE, relatorio)
        logf(f'Relatorio salvo: {relatorio}')

    # Limpa scout.log para o proximo dia
    with open(LOG_FILE, 'w') as f:
        f.write(f'[{data_hoje}] Log reiniciado — proximo scout 07:00\n')

    # Email de resumo
    if novos > 0:
        hoje = datetime.now().strftime('%Y-%m-%d')
        resumo = '\n'.join(
            f'- {l["modelo"]} {l["ano"]} | '
            f'R${l["lance_atual"]:,.0f} | '
            f'margem R${l["margem_estimada"]:,.0f} | '
            f'score {l["score"]}'
            for l in state.values()
            if l.get('added_at', '').startswith(hoje)
        )
        enviar_email(
            f'[MotoBid] Scout {data_hoje}: {novos} lote(s) novo(s)',
            f'Novos lotes encontrados hoje:\n\n{resumo}'
        )

if __name__ == '__main__':
    scout_all()