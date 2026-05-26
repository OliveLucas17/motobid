#!/usr/bin/env python3
import subprocess, re, json, os, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

BRANDAS_EXCLUIDAS = ['honda', 'yamaha', 'shineray']
MARGEM_MINIMA = 3000
EMAIL_NOTIFY = 'lucas170804@gmail.com'

STATE_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/state.json'
LOG_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/scout.log'

SITES = {
    'sumare': {'name': 'Sumare Leiloes', 'color': '#e94560'},
    'ricoleiloes': {'name': 'Rico Leiloes', 'color': '#4a9fd4'},
    'hastasp': {'name': 'Hasta SP', 'color': '#27ae60'},
}

def log(msg):
    ts = datetime.now().strftime('%d/%m %H:%M')
    line = '[' + ts + '] ' + msg
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def crawl(url, render_js=True):
    cmd = ['gsk', 'crawl', url]
    if render_js:
        cmd.append('--render_js')
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.stdout

def detect_brand(text):
    t = text.upper()
    if 'DAFRA' in t: return 'Dafra'
    elif 'KAWASAKI' in t: return 'Kawasaki'
    elif 'BMW' in t: return 'BMW'
    elif 'SUZUKI' in t: return 'Suzuki'
    elif 'KASINSKI' in t: return 'Kasinski'
    elif 'KTM' in t: return 'KTM'
    elif 'APRILIA' in t: return 'Aprilia'
    elif 'ROYAL ENFIELD' in t: return 'Royal Enfield'
    elif 'BAJAJ' in t: return 'Bajaj'
    elif 'HAOJUE' in t or 'HAO JUE' in t: return 'Haojue'
    elif any(b in t for b in ['HONDA', 'YAMAHA', 'SHINERAY']): return 'EXCLUIDA'
    return 'OUTRA'

def has_document(text):
    tl = text.lower()
    kw = ['com direito a documento', 'para circular', 'documento ok',
          'documento original', 'ipva ok', 'licenciado', 'com documentacao']
    return any(k in tl for k in kw)

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
        'Dafra': 10000, 'Kawasaki': 22000, 'BMW': 32000,
        'Suzuki': 14000, 'Kasinski': 8000, 'KTM': 20000,
        'Haojue': 8500, 'Aprilia': 18000, 'Royal Enfield': 16000,
        'Bajaj': 9500, 'Yamaha': 15000, 'Honda': 14000,
    }
    return prices.get(brand, 12000)

def send_email(subject, body):
    try:
        msg = MIMEText(body, 'plain')
        msg['Subject'] = subject
        msg['From'] = 'motobid@alfaemail.com'
        msg['To'] = EMAIL_NOTIFY
        with smtplib.SMTP('localhost', 25, timeout=10) as s:
            s.sendmail('motobid@alfaemail.com', [EMAIL_NOTIFY], msg.as_string())
        log('Email enviado: ' + subject)
    except Exception as e:
        log('Erro email: ' + str(e))
        queue_email(subject, body)

def queue_email(subject, body):
    qfile = '/home/work/.openclaw/workspace/projects/motobid/data/email_queue.json'
    queue = []
    if os.path.exists(qfile):
        try:
            with open(qfile) as f:
                queue = json.load(f)
        except:
            queue = []
    queue.append({'subject': subject, 'body': body, 'ts': datetime.now().isoformat()})
    with open(qfile, 'w') as f:
        json.dump(queue, f)

def add_lot(lot, site_name):
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except:
            state = {}

    lot_id = lot.get('id', 'UNK')
    if lot_id in state:
        log('Lote ' + lot_id + ' ja existe - pulando')
        return False

    lot['fase'] = 'discovery'
    lot['site'] = site_name
    lot['added_at'] = datetime.now().isoformat()
    lot['last_check'] = None
    lot['last_lance'] = lot.get('lance_inicial', 0)

    margin = lot.get('margem_estimada', 0)
    score = min(10, round((margin / 5000) * 7, 1)) if margin > 0 else 0
    lot['score'] = score

    state[lot_id] = lot

    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    modelo = lot.get('modelo', '?')
    lance = lot.get('lance_inicial', 0)
    log('Lote ' + lot_id + ' adicionado: ' + modelo + ' R$' + str(lance))

    subj = '[MotoBid] Novo lote: ' + modelo
    body = 'Novo lote adicionado ao MotoBid\n\n'
    body += 'Lote: ' + lot_id + '\n'
    body += 'Modelo: ' + modelo + ' ' + str(lot.get('ano', '')) + '\n'
    body += 'Marca: ' + str(lot.get('marca', '')) + '\n'
    body += 'Leilao: ' + str(lot.get('leilao', '')) + '\n'
    body += 'Lance: R$ ' + str(lot.get('lance_inicial', 0)) + '\n'
    body += 'Margem est.: R$ ' + str(lot.get('margem_estimada', 0)) + '\n'
    body += 'URL: ' + str(lot.get('url_lote', '')) + '\n\n'
    body += 'MotoBid - AlfaPrime Transportes'
    send_email(subj, body)
    return True

def analyze_text(text, source_url, site_key):
    found = []
    t = text.upper()

    # Find motorcycle mentions
    moto_kw = ['MOTOCICLETA', 'MOTO', 'HONDA', 'YAMAHA', 'SHINERAY', 'DAFRA',
               'KAWASAKI', 'BMW', 'SUZUKI', 'KASINSKI', 'KTM', 'BIZ', 'CG ',
               'FAN ', 'START', 'TITAN', 'CB ', 'NC ', 'XTZ', 'FACT', 'POP ',
               'LEAD', 'PCX', 'XRE', 'NMAX', 'FZ', 'MT-', 'MT ', 'NINJA',
               'Z400', 'Z800', 'Duke', 'RC ', 'Versys', 'Bonneville', 'Dominar']

    lines = text.split('\n')
    for i, line in enumerate(lines):
        if len(line) < 20:
            continue

        brand = detect_brand(line)
        if brand == 'EXCLUIDA':
            continue
        if not has_document(line):
            continue

        price = parse_price(line)
        if price is None or price < 500:
            continue

        # Extract lot number
        lot_match = re.search(r'LOTE[:\\_\\s]*([0-9]{3,4})', line, re.I)
        lot_id = lot_match.group(1) if lot_match else 'UNK-' + str(i)

        # Extract model text
        model_match = re.search(r'(?:MODELO|VEICULO|MOTO)[:\\s]*([^\\n<]{3,60})', line, re.I)
        model = model_match.group(1).strip() if model_match else brand + ' Unknown'

        # Extract year
        year_match = re.search(r'(?:ANO|MODELO)[:\\s]*(\\d{2}/\\d{2})', line, re.I)
        year = year_match.group(1) if year_match else '??/??'

        fipe_est = estimate_fipe(brand, model, year)
        margin = fipe_est - price

        if margin < MARGEM_MINIMA:
            continue

        lot = {
            'id': lot_id,
            'modelo': model[:60],
            'marca': brand,
            'ano': year,
            'lance_inicial': price,
            'fipe': fipe_est,
            'margem_estimada': margin,
            'documento': 'Com direito a documento',
            'leilao': source_url[-30:],
            'leiloeiro': SITES.get(site_key, {}).get('name', site_key),
            'url_lote': source_url,
            'site': site_key,
            'fonte': 'auto_scout',
        }
        found.append(lot)

    return found

def scout_auction(auction_url, site_key):
    log('Scanning: ' + auction_url)
    html = crawl(auction_url)
    if not html or len(html) < 200:
        log('  Pagina vazia')
        return []

    lots = analyze_text(html, auction_url, site_key)
    new_count = 0
    for lot in lots:
        if add_lot(lot, site_key):
            new_count += 1

    log('  -> ' + str(len(lots)) + ' lotes, ' + str(new_count) + ' novos')
    return lots

def scout_all():
    log('=== INICIANDO SCOUT ===')
    results = {}

    # Sumare
    log('--- Sumare ---')
    try:
        html = crawl('https://www.sumareleiloes.com.br/todos-leiloes')
        if html and len(html) > 500:
            ids = re.findall(r'sumareleiloes\\.com\\.br/leiloes/([0-9]+)', html)
            ids = list(dict.fromkeys(ids))[:10]
            log('  ' + str(len(ids)) + ' IDs encontrados')
            for aid in ids:
                url = 'https://www.sumareleiloes.com.br/leiloes/' + aid
                lots = scout_auction(url, 'sumare')
                results['sumare_' + aid] = lots
    except Exception as e:
        log('  Erro: ' + str(e))

    # Rico
    log('--- Rico ---')
    try:
        html = crawl('https://www.ricoleiloes.com.br')
        if html and len(html) > 200:
            ids = re.findall(r'ricoleiloes\\.com\\.br/leiloes/([0-9]+)', html)
            ids = list(dict.fromkeys(ids))[:5]
            for aid in ids:
                url = 'https://www.ricoleiloes.com.br/leiloes/' + aid
                lots = scout_auction(url, 'ricoleiloes')
                results['ricoleiloes_' + aid] = lots
    except Exception as e:
        log('  Erro: ' + str(e))

    # Hasta SP
    log('--- Hasta SP ---')
    try:
        html = crawl('https://www.hastasp.com.br')
        if html and len(html) > 200:
            links = re.findall(r'hastasp\\.com\\.br[^\"\\s]{10,100}', html)
            for link in links[:5]:
                lots = scout_auction(link, 'hastasp')
                results['hastasp_' + link[-20:]] = lots
    except Exception as e:
        log('  Erro: ' + str(e))

    total = sum(len(v) for v in results.values())
    log('=== FIM - ' + str(total) + ' novo(s) ===')
    return results

if __name__ == '__main__':
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    scout_all()