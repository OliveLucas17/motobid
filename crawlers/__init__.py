#!/usr/bin/env python3
"""
crawlers/__init__.py — entrada unificada para todos os crawlers.

Como funciona:
  1. crawl_url()  — faz o crawl de qualquer URL via gsk
  2. crawl_lote() — atualiza lance e status de um lote especifico
"""
import subprocess, time
from utils import log

def crawl_url(url, render_js=True, retries=3, timeout=150):
    for tentativa in range(retries):
        try:
            cmd = ['gsk', 'crawl', url]
            if render_js:
                cmd.append('--render_js')
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if r.stdout and len(r.stdout) > 100:
                return r.stdout  # retorna raw — parser extrai JSON
            log(f'  crawl vazio ({tentativa+1}/{retries}): {url}')
        except subprocess.TimeoutExpired:
            log(f'  timeout ({tentativa+1}/{retries}): {url}')
        except FileNotFoundError:
            log('  gsk nao encontrado')
            return ''
        except Exception as e:
            log(f'  erro: {e}')
        if tentativa < retries - 1:
            time.sleep(2 ** tentativa)
    log(f'  FALHA definitiva: {url}')
    return ''
    

def crawl_lote(lot):
    """
    Faz crawl de um lote especifico para atualizar lance e status.
    Retorna dict com: lance_atual, status, crawl_ok.
    """
    url = lot.get('url_lote', '')

    if not url or url == '#':
        return {
            'lance_atual': lot.get('lance_atual', 0),
            'status':      'sem_url',
            'crawl_ok':    False,
        }

    html = crawl_url(url)

    if not html:
        return {
            'lance_atual': lot.get('lance_atual', 0),
            'status':      'erro_crawl',
            'crawl_ok':    False,
        }

    from utils import extrair_preco

    preco     = extrair_preco(html)
    encerrado = any(k in html.lower() for k in [
        'encerrado', 'leilao encerrado', 'lote encerrado',
        'arrematado', 'vendido', 'leilão encerrado',
    ])

    return {
        'lance_atual': preco or lot.get('lance_atual', 0),
        'status':      'encerrado' if encerrado else 'ativo',
        'crawl_ok':    True,
    }