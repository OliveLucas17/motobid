#!/usr/bin/env python3
"""utils.py — funcoes auxiliares compartilhadas."""
import re, os, json
from datetime import datetime

MARCAS_CONHECIDAS = [
    'HONDA', 'YAMAHA', 'SUZUKI', 'KAWASAKI', 'BMW',
    'DAFRA', 'SHINERAY', 'KTM', 'KASINSKI', 'BAJAJ', 'HAOJUE',
]

def log(msg, arquivo=None):
    ts   = datetime.now().strftime('%d/%m %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if arquivo:
        os.makedirs(os.path.dirname(arquivo) or '.', exist_ok=True)
        with open(arquivo, 'a') as f:
            f.write(line + '\n')

def normalizar_modelo(texto):
    """Remove barra, prefixos do Sumare e lixo do modelo.
    H/HONDA CG 125 TODAY     -> HONDA CG 125 TODAY
    HONDA/XRE 190            -> HONDA XRE 190
    HONDA CG 160 START, 24/24 -> HONDA CG 160 START
    """
    t = texto.upper().strip()
    # Remove barra de prefixo
    t = re.sub(r'^H/(HONDA)', r'HONDA', t)
    for marca in MARCAS_CONHECIDAS:
        t = re.sub(f'^{marca}/', f'{marca} ', t)
    # Remove virgula + ano do final (ex: ", 24/24" ou ", 2024/2024")
    t = re.sub(r',?\s*\d{2,4}/\d{2,4}\s*$', '', t)
    # Remove espacos duplos
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def detectar_marca(texto):
    t = texto.upper()
    for marca in MARCAS_CONHECIDAS:
        if marca in t:
            return marca
    return None

def extrair_ano(bloco):
    """Retorna (string '2023/2024', int 2023) ou (None, None)."""
    m = re.search(r'\b(20\d{2})/(20\d{2})\b', bloco)
    if m:
        return f'{m.group(1)}/{m.group(2)}', int(m.group(1))
    m = re.search(r'\b(\d{2})/(\d{2})\b', bloco)
    if m:
        a1 = int('20' + m.group(1))
        a2 = int('20' + m.group(2))
        if 2000 <= a1 <= 2030:
            return f'{a1}/{a2}', a1
    return None, None

def extrair_preco(bloco):
    """Extrai preco em R$ e retorna float."""
    patterns = [
        r'R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)',
        r'Lance[\:\s]+R\$\s*([0-9.,]+)',
        r'Valor[\:\s]+R\$\s*([0-9.,]+)',
    ]
    for p in patterns:
        m = re.search(p, bloco, re.I)
        if m:
            raw = m.group(1).strip()
            try:
                if ',' in raw:
                    return float(raw.replace('.', '').replace(',', '.'))
                else:
                    return float(raw.replace('.', ''))
            except:
                continue
    return None

def extrair_cor(bloco):
    m = re.search(r'(?:COR|Cor)[\:\s]+([A-Za-z]+)', bloco)
    if m:
        return m.group(1).capitalize()
    for cor in ['PRETO', 'BRANCO', 'VERMELHO', 'PRATA', 'CINZA', 'AZUL']:
        if cor in bloco.upper():
            return cor.capitalize()
    return ''

def extrair_lote_id(bloco, url=''):
    m = re.search(r'Lote[\:\s#]*(\d{3,5})', bloco, re.I)
    if m:
        return m.group(1)
    m = re.search(r'/lotes/([a-f0-9\-]{8,})', url)
    if m:
        return m.group(1)[:12]
    return None

def doc_ok(texto):
    from config import DOC_OK_KEYWORDS, SUCATA_KEYWORDS
    tl = texto.lower()
    if any(k in tl for k in SUCATA_KEYWORDS):
        return False
    return any(k in tl for k in DOC_OK_KEYWORDS)

def ano_valido(ano_int):
    from config import ANO_MINIMO
    return ano_int is not None and ano_int >= ANO_MINIMO

def carregar_json(path, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return default

def salvar_json(path, data):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fmt_brl(valor):
    return f"R$ {int(valor):,}".replace(',', '.')