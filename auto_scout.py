#!/usr/bin/env python3
'''
AUTO_SCOUT — MotoBid
Varredura automática de novos lotes com ranking por marca.
Referência de preço: Facebook Marketplace (realismo brasileiro).
'''
import subprocess, re, json, os, smtplib, time
from datetime import datetime

STATE_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/state.json'
LOG_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/scout.log'

from config import (
    TIER_TOP, TIER_HIGH, TIER_OTHER, EXCLUDED, SUCATA_EXCLUDED,
    MARGEM_MIN_TIER1, MARGEM_MIN_TIER2, MARGEM_MIN_TIER3,
    LANCE_MINIMO, LANCE_MAXIMO, SCORE_MINIMO,
    DOC_OK_KEYWORDS, PREFETURA_KEYWORDS, DETRAN_EXCLUDED,
    FB_MARKETPLACE_PRICES, FIPE_PRICES,
    EMAIL_TO
)

def log(msg):
    ts = datetime.now().strftime('%d/%m %H:%M')
    line = '[' + ts + '] ' + msg
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def get_tier(brand):
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
    return '?'

def get_tier_score(tier):
    if tier == 1: return 10
    if tier == 2: return 8
    if tier == 3: return 6
    return 0

def get_price_ref(model, brand):
    '''Tenta FB Marketplace primeiro, fallback FIPE.'''
    key = (brand.upper() + ' ' + model.upper()).strip()
    for fb_key in FB_MARKETPLACE_PRICES:
        if fb_key in key or key in fb_key:
            return FB_MARKETPLACE_PRICES[fb_key], 'FB'
    # Fallback FIPE
    for fipe_key in FIPE_PRICES:
        if fipe_key.upper() in key:
            return FIPE_PRICES[fipe_key], 'FIPE'
    return None, None

def crawl(url, retries=3):
    for attempt in range(retries):
        try:
            cmd = ['gsk', 'crawl', url, '--render_js']
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
            text = r.stdout
            if text and len(text) > 200:
                return text
            time.sleep(2 ** attempt)
        except:
            time.sleep(2 ** attempt)
    return ''

def detect_brand(text):
    t = text.upper()
    for b in ['HONDA', 'YAMAHA', 'SUZUKI', 'DAFRA', 'KAWASAKI', 'BMW', 'KASINSKI', 'KTM', 'SHINERAY', 'HAOJUE', 'ROYAL ENFIELD']:
        if b in t:
            return b
    return 'OUTRA'

def is_document_ok(text):
    tl = text.lower()
    if any(k in tl for k in SUCATA_EXCLUDED):
        return False
    return any(k in tl for k in DOC_OK_KEYWORDS)

def is_prefeitura(text):
    tl = text.lower()
    if any(k in tl for k in DETRAN_EXCLUDED):
        return False
    return any(k in tl for k in PREFETURA_KEYWORDS)

def parse_price(text):
    m = re.search(r'R?\\$?\\s*([0-9]{1,3}(?:\\.[0-9]{3})*(?:,[0-9]{2})?)', text)
    if m:
        try:
            return float(m.group(1).replace('.', '').replace(',', '.'))
        except:
            pass
    return None

def extract_model(text):
    model_m = re.search(r'(?:MODELO|VEICULO|MOTO)[:\\s]*([^\\n<]{3,70})', text, re.I)
    if model_m:
        return model_m.group(1).strip()[:70]
    # Try pattern like HONDA/CG 125 TITAN
    m2 = re.search(r'([A-Z]{2,15})/([A-Z0-9 \\-]{3,50})', text)
    if m2:
        return m2.group(1) + ' ' + m2.group(2).strip()
    return ''

def calculate_score(tier, margem, documento_ok, ano):
    base = get_tier_score(tier)
    doc_bonus = 2 if documento_ok else 0
    margin_score = min(5, round((margem / 1500) * 3, 1))
    year_bonus = 0
    try:
        y = int(ano[:2]) if len(ano) >= 2 else 0
        if y >= 22: year_bonus = 1.5
        elif y >= 20: year_bonus = 0.5
    except:
        pass
    return round(min(10, base + doc_bonus + margin_score + year_bonus), 1)

def send_email(subject, body):
    try:
        msg = smtplib.MIMEText(body, 'plain')
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
    margem = lot.get('margem_estimada', 0)
    tier = lot.get('tier', 0)
    tier_name = get_tier_name(tier)
    tier_icon = {'TOP': '[HOND/YAM]', 'ALTA': '[ALTAS]', 'OUTRAS': '[OUTRAS]', '?': '[?]'}
    log('NOVO LOTE: ' + lot_id + ' | ' + modelo + ' | R$ ' + str(lance) + ' | margem R$ ' + str(margem) + ' | ' + tier_icon.get(tier_name, ''))

    subj = '[MotoBid] Novo lote: ' + modelo + ' | R$ ' + str(margem) + ' margem'
    body = 'Novo lote adicionado ao MotoBid\n\n'
    body += 'ID: ' + lot_id + '\n'
    body += 'Modelo: ' + modelo + ' ' + str(lot.get('ano', '')) + '\n'
    body += 'Marca: ' + str(lot.get('marca', '')) + '\n'
    body += 'Tier: ' + tier_icon.get(tier_name, '') + '\n'
    body += 'Leilao: ' + str(lot.get('leilao', '')) + '\n'
    body += 'Lance: R$ ' + str(lot.get('lance_inicial', 0)) + '\n'
    body += 'Preco Ref (' + str(lot.get('price_ref', '?')) + '): R$ ' + str(lot.get('preco_ref', 0)) + '\n'
    body += 'Margem: R$ ' + str(lot.get('margem_estimada', 0)) + '\n'
    body += 'Score: ' + str(lot.get('score', 0)) + '/10\n'
    body += 'Documento: ' + ('SIM' if lot.get('documento_ok') else 'NAO') + '\n'
    body += 'URL: ' + str(lot.get('url_lote', '')) + '\n\n'
    body += 'MotoBid - AlfaPrime Transportes'
    send_email(subj, body)
    return True

def analyze_block(block, source_url, site_key):
    if len(block) < 80:
        return None

    brand = detect_brand(block)
    if brand == 'OUTRA' or brand in EXCLUDED:
        return None

    if not is_document_ok(block):
        return None

    price = parse_price(block)
    if price is None or price < LANCE_MINIMO or price > LANCE_MAXIMO:
        return None

    tier = get_tier(brand)
    if tier == 0:
        return None

    margem_min = get_margem_min(tier)

    model = extract_model(block)
    if not model:
        model = brand + ' Unknown'

    year_m = re.search(r'(?:ANO|MODELO)[:\\s]*(\\d{2}/\\d{2})', block, re.I)
    year = year_m.group(1) if year_m else '??/??'

    # Get price reference (FB or FIPE)
    preco_ref, ref_type = get_price_ref(model, brand)
    if preco_ref is None:
        # Estimate from tier
        if tier == 1: preco_ref = 15500
        elif tier == 2: preco_ref = 13000
        else: preco_ref = 10000
        ref_type = 'EST'

    margem = preco_ref - price

    if margem < margem_min:
        return None

    score = calculate_score(tier, margem, True, year)
    if score < SCORE_MINIMO:
        return None

    lot_id_m = re.search(r'LOTE[:\\_\\s#]*([0-9]{3,5})', block, re.I)
    lot_id = lot_id_m.group(1) if lot_id_m else 'UNK-' + str(hash(block) % 9999)

    cor_m = re.search(r'COR[:\\s]*([^\\n<,]{3,30})', block, re.I)
    cor = cor_m.group(1).strip() if cor_m else ''

    return {
        'id': lot_id,
        'modelo': model,
        'marca': brand,
        'ano': year,
        'cor': cor,
        'tier': tier,
        'tier_name': get_tier_name(tier),
        'lance_inicial': price,
        'lance_atual': price,
        'preco_ref': preco_ref,
        'price_ref': ref_type,
        'margem_estimada': margem,
        'score': score,
        'documento_ok': True,
        'leilao': site_key + '_leilao',
        'url_lote': source_url,
        'site': site_key,
        'fonte': 'auto_scout',
    }

def scout_auction(url, site_key, is_prefeitura_auction=True):
    log('Scanning: ' + url)
    html = crawl(url)
    if not html or len(html) < 200:
        log('  Pagina vazia')
        return []

    # If not prefeitura, skip
    if is_prefeitura_auction and not is_prefeitura(html):
        log('  Nao eh prefeitura/DETRAN - pulando')
        return []

    found = []
    lines = html.split('\n')
    blocks = []
    current = []
    for line in lines:
        if len(line.strip()) > 10:
            current.append(line)
        elif current:
            blocks.append('\n'.join(current))
            current = []
    if current:
        blocks.append('\n'.join(current))

    for block in blocks:
        lot = analyze_block(block, url, site_key)
        if lot:
            found.append(lot)
            add_lot(lot)

    log('  -> ' + str(len(found)) + ' lotes validos')
    return found

def scout_all():
    log('=== MOTOBD SCOUT ===')
    results = {}

    # Sumare - scan all auction pages
    log('--- Sumare Leiloes ---')
    r = subprocess.run(['gsk', 'search', 'site:sumareleiloes.com.br/leiloes/'], capture_output=True, text=True, timeout=30)
    auction_ids = []
    if r.stdout:
        try:
            data = json.loads(r.stdout)
            for item in data.get('data', {}).get('organic_results', []):
                link = item.get('link', '')
                ids = re.findall(r'leiloes?/([0-9]{3,6})', link)
                auction_ids.extend(ids)
        except:
            pass
    auction_ids = list(dict.fromkeys(auction_ids))[:15]

    log('  Encontrados ' + str(len(auction_ids)) + ' leiloes')
    for aid in auction_ids:
        try:
            url = 'https://www.sumareleiloes.com.br/leiloes/' + aid
            lots = scout_auction(url, 'sumare')
            if lots:
                results['sumare_' + aid] = lots
        except Exception as e:
            log('  Erro no ' + aid + ': ' + str(e))

    # Rico
    log('--- Rico Leiloes ---')
    lots = scout_auction('https://www.ricoleiloes.com.br', 'ricoleiloes', is_prefeitura_auction=False)
    if lots:
        results['ricoleiloes'] = lots

    # Hasta SP
    log('--- Hasta SP ---')
    lots = scout_auction('https://www.hastasp.com.br', 'hastasp', is_prefeitura_auction=False)
    if lots:
        results['hastasp'] = lots

    total = sum(len(v) for v in results.values())
    log('=== FIM - ' + str(total) + ' lote(s) validos ===')
    return results

if __name__ == '__main__':
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    scout_all()