#!/usr/bin/env python3
import subprocess, re, time

def crawl_with_retry(url, retries=3):
    for attempt in range(retries):
        try:
            cmd = ['gsk', 'crawl', url, '--render_js']
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            text = r.stdout
            if text and len(text) > 200:
                return text
            time.sleep(2 ** attempt)
        except:
            time.sleep(2 ** attempt)
    return ''

def crawl_lote_hastasp(lote):
    url = lote.get('url_lote') or 'https://www.hastasp.com.br'
    text = crawl_with_retry(url)
    
    data = {
        'lance_atual': 0.0,
        'lance_inicial': lote.get('lance_inicial', 0),
        'status': 'desconhecido',
        'data_encerramento': None,
        'html_snippet': text[:2000],
        'erro': None,
    }
    
    if not text or len(text) < 200:
        data['erro'] = 'pagina vazia'
        return data
    
    text_lower = text.lower()
    
    if 'encerrado' in text_lower or 'finalizado' in text_lower:
        data['status'] = 'encerrado'
    elif 'aberto' in text_lower:
        data['status'] = 'lance_registrado' if 'lance' in text_lower else 'aberto_sem_lance'
    
    prices = re.findall(r'R\\$\\s*([0-9]{1,3}(?:\\.[0-9]{3})*,[0-9]{2})', text)
    for price_str in prices:
        try:
            val = float(price_str.replace('.', '').replace(',', '.'))
            if 50 < val < 500000:
                data['lance_atual'] = val
                break
        except:
            pass
    
    if data['lance_atual'] == 0:
        data['lance_atual'] = lote.get('lance_inicial', 0)
    
    return data