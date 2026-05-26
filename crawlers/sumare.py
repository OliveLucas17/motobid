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
        except Exception as e:
            time.sleep(2 ** attempt)
    return ''

def crawl_lote_sumare(lote):
    url = lote['url_lote']
    text = crawl_with_retry(url)
    
    data = {
        'lance_atual': 0.0,
        'lance_inicial': lote.get('lance_inicial', 0),
        'status': 'desconhecido',
        'data_encerramento': lote.get('data_encerramento'),
        'html_snippet': text[:2000],
        'erro': None,
    }
    
    if not text or len(text) < 200:
        data['erro'] = 'pagina vazia'
        return data
    
    text_lower = text.lower()
    
    if 'encerrado' in text_lower or 'vendido' in text_lower:
        data['status'] = 'encerrado'
    elif 'aberto' in text_lower:
        if 'lance' in text_lower:
            data['status'] = 'lance_registrado'
        else:
            data['status'] = 'aberto_sem_lance'
    
    patterns = [
        r'Lance Atual[:\/\\-]*\n?\r?\t?\f?\u200b?\u200c?([R$\/A-Za-z0-9.\/\\_\u00a0-\u00ff ]{5,80})',
        r'Lance[:\/\\_]*\n?\r?\t?([R$\/A-Za-z0-9.\/\\_\u00a0-\u00ff ]{5,80})',
        r'R\\$\\s*([0-9]{1,3}(?:\\.[0-9]{3})*,[0-9]{2})',
    ]
    
    for pattern in patterns:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            raw = m.group(1)
            clean = re.sub(r'[^0-9.,]', '', raw)
            if not clean:
                clean = re.sub(r'[^0-9.,]', '', m.group(0))
            try:
                val = float(clean.replace('.', '').replace(',', '.'))
                if 100 < val < 1000000:
                    data['lance_atual'] = val
                    break
            except:
                pass
    
    if data['lance_atual'] == 0:
        data['lance_atual'] = lote.get('lance_inicial', 0)
    
    date_patterns = [
        r'Fechamento[:\/\\_\n\r\t ]+([A-Z][a-z]{2,8}[ ]+[0-9]{1,2}[ ]+[A-Z][a-z]{2,8}[ ]+[0-9]{2,4}[ ]*[0-9]{1,2}:[0-9]{2})',
        r'Fechamento[:\/\\_\n\r\t ]+([0-9]{1,2}[ \/]+[A-Za-z]{3,9}[ \/]+[0-9]{2,4})',
        r'Encerramento[:\/\\_\n\r\t ]+([0-9]{1,2}[\\/][0-9]{1,2}[\\/][0-9]{2,4})',
    ]
    for p in date_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            data['data_encerramento'] = m.group(1).strip()
            break
    
    return data