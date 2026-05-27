#!/usr/bin/env python3
"""
crawlers/__init__.py — entrada unificada para todos os crawlers.
Usa playwright em vez de gsk crawl — funciona em qualquer maquina.
"""
import time, json
from utils import log

def crawl_url(url, render_js=True, retries=3, timeout=30):
    """
    Crawl de uma URL usando playwright (chromium headless).
    Substitui o gsk crawl --render_js sem depender do Genspark.
    """
    for tentativa in range(retries):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page    = browser.new_page()
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                page.goto(url, timeout=timeout * 1000, wait_until='networkidle')
                conteudo = page.content()
                browser.close()

                if conteudo and len(conteudo) > 300:
                    return conteudo

            log(f'  crawl vazio ({tentativa+1}/{retries}): {url}')
        except Exception as e:
            log(f'  crawl erro ({tentativa+1}/{retries}): {e}')

        if tentativa < retries - 1:
            time.sleep(2 ** tentativa)

    log(f'  FALHA definitiva: {url}')
    return ''

def crawl_lote(lot):
    url = lot.get('url_lote', '')
    if not url or url == '#':
        return {'lance_atual': lot.get('lance_atual', 0), 'status': 'sem_url', 'crawl_ok': False}

    html = crawl_url(url)
    if not html:
        return {'lance_atual': lot.get('lance_atual', 0), 'status': 'erro_crawl', 'crawl_ok': False}

    from utils import extrair_preco
    preco     = extrair_preco(html)
    encerrado = any(k in html.lower() for k in [
        'encerrado', 'leilao encerrado', 'arrematado', 'vendido'
    ])
    return {
        'lance_atual': preco or lot.get('lance_atual', 0),
        'status':      'encerrado' if encerrado else 'ativo',
        'crawl_ok':    True,
    }