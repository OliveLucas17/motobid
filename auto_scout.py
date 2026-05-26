#!/usr/bin/env python3
'''
AUTO_SCOUT — MotoBid
Varredura automática de novos lotes com ranking por marca.
'''
import subprocess, re, json, os, smtplib
from datetime import datetime
from email.mime.text import MIMEText

STATE_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/state.json'
LOG_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/scout.log'

# Import config
from config import (
    TIER_TOP, TIER_HIGH, TIER_OTHER, EXCLUDED,
    MARGEM_MIN_TIER1, MARGEM_MIN_TIER2, MARGEM_MIN_TIER3,
    LANCE_MINIMO, LANCE_MAXIMO, SCORE_MINIMO,
    DOC_KEYWORDS, EMAIL_TO
)

def log(msg):
    ts = datetime.now().strftime('%d/%m %H:%M')
    line = '[' + ts + '] ' + msg
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def get_brand_tier(brand):
    b = brand.upper()
    if b in TIER_TOP: return 1
    if b in TIER_HIGH: return 2
    if b in TIER_OTHER: return 3
    return 0

def get_margem_min(tier):
    if tier == 1: return MARGEM_MIN_TIER1
    if tier == 2: return MARGEM_MIN_TIER2
    if tier == 3: return MARGEM_MIN_TIER3
    return 999999

def get_tier_name(tier):
    if tier == 1: return 'TOP'
    if tier == 2: return 'ALTA'
    if tier == 3: return 'OUTRAS'
    return 'EXCLUIDA'

def get_tier_score(tier):
    if tier == 1: return 10
    if tier == 2: return 8
    if tier == 3: return 6
    return 0

def crawl(url, retries=3):
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

import time

def detect_brand(text):
    t = text.upper()
    if any(b in t for b in EXCLUDED): return 'EXCLUIDA'
    if 'HONDA' in t: return 'HONDA'
    if 'YAMAHA' in t: return 'YAMAHA'
    if 'SUZUKI' in t: return 'SUZUKI'
    if 'DAFRA' in t: return 'DAFRA'
    if 'KAWASAKI' in t: return 'KAWASAKI'
    if 'BMW' in t: return 'BMW'
    if 'KASINSKI' in t: return 'KASINSKI'
    if 'KTM' in t: return 'KTM'
    if 'APRILIA' in t: return 'APRILIA'
    if 'ROYAL ENFIELD' in t: return 'ROYAL ENFIELD'
    if 'BAJAJ' in t: return 'BAJAJ'
    if 'HAOJUE' in t or 'HAO JUE' in t: return 'HAOJUE'
    if 'SHINERAY' in t: return 'SHINERAY'
    return 'OUTRA'

def has_document(text):
    tl = text.lower()
    return any(k in tl for k in DOC_KEYWORDS)

def parse_price(text):
    m = re.search(r'R\\$\\s*([0-9]{1,3}(?:\\.[0-9]{3})*,[0-9]{2})', text)
    if m:
        try:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    return None

def estimate_fipe(brand, model, year):
    prices = {
        'HONDA': {'biz': 11000, 'cg': 14500, 'fan': 15000, 'start': 15500, 'titan': 15500, 'cb300': 17000, 'xre': 19000, 'pcx': 16000, 'nc': 22000, ' Bros': 14000, 'pop': 12000},
        'YAMAHA': {'fazer': 15000, 'mt': 17000, 'tenere': 22000, 'factor': 13000, 'crypton': 11000, 'xtz': 15500, 'yj': 11000, 'yzf': 18000, 'nmax': 16500, 'neo': 13000, 'szr': 13000},
        'SUZUKI': {'yes': 14000, 'inazuma': 13000, 'vstrom': 22000, 'gs': 20000, 'bandit': 18000, 'burgman': 16000, 'yescom': 14000},
        'DAFRA': {'city': 9500, 'road': 11000, 'sport': 13000, 'next': 9000, 'laser': 8500, 'delta': 9000},
        'KAWASAKI': {'ninja': 25000, 'z': 22000, 'versys': 24000, 'er6': 20000, 'klr': 22000},
        'BMW': {'gs': 35000, 'f800': 28000, 'r1200': 42000, 'g310': 22000},
        'KASINSKI': {'otr': 8500, 'win': 8000, 'mirim': 7500},
        'KTM': {'duke': 18000, 'rc': 22000, 'adv': 25000},
        'HAOJUE': {'dr160': 8500, 'nx': 9000, 'rz': 8000},
    }
    brand_prices = prices.get(brand, {})
    model_up = model.upper()
    for key, price in brand_prices.items():
        if key.upper() in model_up:
            return price
    return brand_prices.get(list(brand_prices.keys())[0], 13000) if brand_prices else 13000

def calculate_score(tier, margem, documento_ok, ano):
    base = get_tier_score(tier)
    doc_bonus = 2 if documento_ok else 0
    margin_score = min(5, round((margem / 3000) * 3, 1))
    year_bonus = 0
    try:
        if int(ano[:2]) >= 22:
            year_bonus = 1.5
        elif int(ano[:2]) >= 20:
            year_bonus = 0.5
    except:
        pass
    return round(min(10, base + doc_bonus + margin_score + year_bonus), 1)

def send_email(subject, body):
    try:
        msg = MIMEText(body, 'plain')
        msg['Subject'] = subject
        msg['From'] = 'motobid@alfaemail.com'
        msg['To'] = EMAIL_TO
        with smtplib.SMTP('localhost', 25, timeout=10) as s:
            s.sendmail('motobid@alfaemail.com', [EMAIL_TO], msg.as_string())
        log('Email enviado')
    except Exception as e:
        log('Erro email: ' + str(e))

def add_lot(lot):
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except:
            state = {}

    lot_id = lot.get('id', 'UNK')
    if lot_id in state:
        log('Lote ' + lot_id + ' ja existe')
        return False

    lot['fase'] = 'discovery'
    lot['added_at'] = datetime.now().isoformat()
    lot['last_check'] = None
    lot['last_lance'] = lot.get('lance_inicial', 0)

    state[lot_id] = lot

    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    modelo = lot.get('modelo', '?')
    lance = lot.get('lance_inicial', 0)
    tier_name = get_tier_name(lot.get('tier', 0))
    tier_icon = {'TOP': '⭐', 'ALTA': '🔷', 'OUTRAS': '📦', 'EXCLUIDA': '❌'}
    log('Lote ' + lot_id + ' adicionado: ' + modelo + ' R$' + str(lance) + ' [' + tier_icon.get(tier_name, '') + ' ' + tier_name + ']')

    subj = '[MotoBid] Novo lote: ' + modelo + ' [' + tier_name + ']'
    body = 'Novo lote adicionado ao MotoBid\n\n'
    body += 'Lote: ' + lot_id + '\n'
    body += 'Modelo: ' + modelo + ' ' + str(lot.get('ano', '')) + '\n'
    body += 'Marca: ' + str(lot.get('marca', '')) + '\n'
    body += 'Tier: ' + tier_icon.get(tier_name, '') + ' ' + tier_name + '\n'
    body += 'Leilao: ' + str(lot.get('leilao', '')) + '\n'
    body += 'Lance: R$ ' + str(lot.get('lance_inicial', 0)) + '\n'
    body += 'FIPE: R$ ' + str(lot.get('fipe', 0)) + '\n'
    body += 'Margem: R$ ' + str(lot.get('margem_estimada', 0)) + '\n'
    body += 'Score: ' + str(lot.get('score', 0)) + '/10\n'
    body += 'Documento: ' + ('SIM' if lot.get('documento_ok') else 'NAO') + '\n'
    body += 'URL: ' + str(lot.get('url_lote', '')) + '\n\n'
    body += 'MotoBid - AlfaPrime Transportes'
    send_email(subj, body)
    return True

def analyze_block(block, source_url, site_key):
    if len(block) < 60:
        return None

    brand = detect_brand(block)
    if brand == 'EXCLUIDA':
        return None

    if not has_document(block):
        return None

    price = parse_price(block)
    if price is None or price < LANCE_MINIMO or price > LANCE_MAXIMO:
        return None

    tier = get_brand_tier(brand)
    if tier == 0:
        return None

    margem_min = get_margem_min(tier)

    # Extract model
    model_match = re.search(r'(?:MODELO|VEICULO|MOTO|VEICULO)[:\\s]*([^\\n<]{3,60})', block, re.I)
    model = model_match.group(1).strip() if model_match else brand + ' Unknown'
    model = model[:70]

    # Extract year
    year_match = re.search(r'(?:ANO|MODELO)[:\\s]*(\\d{2}/\\d{2})', block, re.I)
    year = year_match.group(1) if year_match else '??/??'

    fipe = estimate_fipe(brand, model, year)
    margem = fipe - price

    if margem < margem_min:
        return None

    score = calculate_score(tier, margem, True, year)
    if score < SCORE_MINIMO:
        return None

    # Lot ID
    lot_match = re.search(r'LOTE[:\\_\\s]*([0-9]{3,4})', block, re.I)
    lot_id = lot_match.group(1) if lot_match else 'UNK-' + str(hash(block) % 9999)

    # Extract color
    color_match = re.search(r'(?:COR|COR\\/ACESSORIOS)[:\\s]*([^\\n<,]{3,30})', block, re.I)
    cor = color_match.group(1).strip() if color_match else ''

    return {
        'id': lot_id,
        'modelo': model,
        'marca': brand,
        'ano': year,
        'cor': cor,
        'tier': tier,
        'tier_name': get_tier_name(tier),
        'lance_inicial': price,
        'fipe': fipe,
        'margem_estimada': margem,
        'score': score,
        'documento_ok': True,
        'leilao': source_url[-30:],
        'url_lote': source_url,
        'site': site_key,
        'fonte': 'auto_scout',
    }

def scout_auction(url, site_key):
    log('Scanning: ' + url)
    html = crawl(url)
    if not html or len(html) < 200:
        log('  Pagina vazia')
        return []

    found = []
    blocks = html.split('\n')
    for i, line in enumerate(blocks):
        lot = analyze_block(line, url, site_key)
        if lot:
            found.append(lot)

    new_count = sum(1 for lot in found if add_lot(lot))
    log('  -> ' + str(len(found)) + ' lotes, ' + str(new_count) + ' novos')
    return found

def scout_all():
    log('=== MOTOBD SCOUT ===')
    results = {}

    # Sumare
    log('--- Sumare ---')
    try:
        html = crawl('https://www.sumareleiloes.com.br/todos-leiloes')
        if html and len(html) > 500:
            ids = list(dict.fromkeys(re.findall(r'sumareleiloes\\.com\\.br/leiloes/([0-9]+)', html)))[:10]
            log('  ' + str(len(ids)) + ' leiloes encontrados')
            for aid in ids:
                lots = scout_auction('https://www.sumareleiloes.com.br/leiloes/' + aid, 'sumare')
                results['sumare_' + aid] = lots
    except Exception as e:
        log('  Erro: ' + str(e))

    # Rico
    log('--- Rico ---')
    try:
        html = crawl('https://www.ricoleiloes.com.br')
        if html and len(html) > 200:
            ids = list(dict.fromkeys(re.findall(r'ricoleiloes\\.com\\.br/leiloes/([0-9]+)', html)))[:5]
            for aid in ids:
                lots = scout_auction('https://www.ricoleiloes.com.br/leiloes/' + aid, 'ricoleiloes')
                results['ricoleiloes_' + aid] = lots
    except Exception as e:
        log('  Erro: ' + str(e))

    # Hasta SP
    log('--- Hasta SP ---')
    try:
        html = crawl('https://www.hastasp.com.br')
        if html and len(html) > 200:
            links = list(dict.fromkeys(re.findall(r'hastasp\\.com\\.br[^\"\\s]{10,100}', html)))[:5]
            for link in links:
                lots = scout_auction(link, 'hastasp')
                results['hastasp_' + link[-20:]] = lots
    except Exception as e:
        log('  Erro: ' + str(e))

    total = sum(len(v) for v in results.values())
    log('=== FIM - ' + str(total) + ' lote(s) novo(s) ===')
    return results

if __name__ == '__main__':
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    scout_all()