#!/usr/bin/env python3
import subprocess, re, json, os

STATE_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/state.json'

# Load current state to avoid duplicates
existing = []
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        data = json.load(f)
        existing = list(data.keys())

print(f'Current lots in monitoring: {len(existing)}')
print(f'Existing IDs: {existing}')

# Get all auction IDs from Sumare
result = subprocess.run(
    ['gsk', 'search', 'site:sumareleiloes.com.br leiloes'],
    capture_output=True, text=True, timeout=30
)
print('Search output:', result.stdout[:300])

# Try to get the main auction list page
r2 = subprocess.run(
    ['gsk', 'crawl', 'https://www.sumareleiloes.com.br/todos-leiloes', '--render_js'],
    capture_output=True, text=True, timeout=120
)
html = r2.stdout
print(f'HTML length: {len(html)}')

if html and len(html) > 200:
    # Find auction IDs
    auction_ids = list(dict.fromkeys(re.findall(r'sumareleiloes\\.com\\.br/leiloes/([0-9]+)', html)))
    print(f'Found {len(auction_ids)} auction IDs: {auction_ids[:10]}')

    for aid in auction_ids[:10]:
        # Check each auction
        r3 = subprocess.run(
            ['gsk', 'crawl', f'https://www.sumareleiloes.com.br/leiloes/{aid}', '--render_js'],
            capture_output=True, text=True, timeout=120
        )
        h = r3.stdout
        if h and len(h) > 500:
            # Find moto-related content
            moto_blocks = re.findall(r'(?:moto|veículo|veiculo|carro)[^<]{10,200}', h, re.I)
            print(f'  Auction {aid}: {len(h)} chars, {len(moto_blocks)} moto mentions')
            # Find lot IDs
            lots = re.findall(r'lotes?/([a-z0-9-]{20,50})', h)
            print(f'    Lot URLs: {len(lots)} found')
        else:
            print(f'  Auction {aid}: empty or short ({len(h) if h else 0} chars)')
else:
    print('No HTML from todos-leiloes page')
    # Try homepage
    r4 = subprocess.run(
        ['gsk', 'crawl', 'https://www.sumareleiloes.com.br', '--render_js'],
        capture_output=True, text=True, timeout=120
    )
    h2 = r4.stdout
    print(f'Homepage: {len(h2)} chars')
    if h2:
        auction_ids2 = list(dict.fromkeys(re.findall(r'sumareleiloes\\.com\\.br/leiloes/([0-9]+)', h2)))
        print(f'Auction IDs from homepage: {auction_ids2[:10]}')