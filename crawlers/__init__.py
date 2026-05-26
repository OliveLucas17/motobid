#!/usr/bin/env python3
'''Crawlers do MotoBid — um por plataforma'''
from .sumare import crawl_lote_sumare
from .ricoleiloes import crawl_lote_ricoleiloes
from .hastasp import crawl_lote_hastasp

def crawl(lote):
    site = lote.get('site', 'sumare')
    if site == 'ricoleiloes':
        return crawl_lote_ricoleiloes(lote)
    elif site == 'hastasp':
        return crawl_lote_hastasp(lote)
    else:
        return crawl_lote_sumare(lote)