#!/usr/bin/env python3
'''
CONFIG — MotoBid
Filtros e thresholds para análise de lotes de leilão
'''

# ============================================================
# RANKING DE MARCAS (por potencial de revenda)
# ============================================================
TIER_TOP = ['HONDA', 'YAMAHA']
TIER_HIGH = ['SUZUKI', 'DAFRA', 'KAWASAKI', 'BMW']
TIER_OTHER = ['KASINSKI', 'KTM', 'APRILIA', 'ROYAL ENFIELD', 'BAJAJ', 'HAOJUE']
EXCLUDED = ['SHINERAY', 'SUCATA', 'MOTOR INSERVIDO']

# ============================================================
# THRESHOLDS — margem mínima por tier (R$)
# ============================================================
# Atualizado: margem a partir de R$ 1.000 (realismo do mercado de motos)
MARGEM_MIN_TIER1 = 1000   # Honda, Yamaha
MARGEM_MIN_TIER2 = 2000   # Suzuki, Dafra, Kawasaki, BMW
MARGEM_MIN_TIER3 = 2500   # Outras

LANCE_MINIMO = 300
LANCE_MAXIMO = 100000

SCORE_MINIMO = 4.0  # baixou de 5.0 para aceitar mais oportunidades

# ============================================================
# DOCUMENTO
# ============================================================
DOC_OK_KEYWORDS = [
    'com direito a documento', 'para circular', 'documento ok',
    'documento original', 'ipva ok', 'licenciado', 'documentacao ok',
    'placa verde', 'veiculo conservado'
]
SUCATA_EXCLUDED = ['sucata', 'motor inserido', 'sem documento', 'sem direito']

# ============================================================
# REFERENCIA DE PREÇO — Facebook Marketplace
# ============================================================
# Preços de referência Facebook Marketplace Brasil (2026)
# Usar como base para cálculo de margem real
FB_MARKETPLACE_PRICES = {
    'HONDA CG 160 START': 15500,
    'HONDA CG 160 FAN': 15000,
    'HONDA CG 160 TITAN': 15500,
    'HONDA BIZ 125': 11000,
    'HONDA PCX 150': 16000,
    'HONDA CB 300': 17000,
    'HONDA XRE 300': 19000,
    'HONDA Bros 160': 14000,
    'HONDA POP 110': 12000,
    'YAMAHA FAZER 250': 15000,
    'YAMAHA FACTOR 150': 13000,
    'YAMAHA NMAX 160': 16500,
    'YAMAHA XTZ 250': 15500,
    'YAMAHA CRYPTON 110': 11000,
    'YAMAHA TENERE 250': 22000,
    'SUZUKI YES 125': 14000,
    'SUZUKI INAZUMA 250': 13000,
    'SUZUKI VSTROM 650': 35000,
    'SUZUKI BURGMAN 200': 16000,
    'DAFRA CITY 150': 9500,
    'DAFRA ROAD 150': 11000,
    'DAFRA SPORT 150': 13000,
    'KAWASAKI NINJA 300': 25000,
    'KAWASAKI Z 650': 22000,
    'KAWASAKI VERSYS 300': 24000,
    'BMW G310R': 22000,
    'BMW GS 1200': 42000,
    'KASINSKI OTR 150': 8500,
    'KTM DUKE 200': 18000,
}

# ============================================================
# FIPE (fallback quando não tem FB)
# ============================================================
FIPE_PRICES = {
    'HONDA CG 160': 16500,
    'HONDA BIZ 125': 11000,
    'HONDA PCX': 16000,
    'YAMAHA Fazer 250': 15000,
    'YAMAHA Factor 150': 13000,
    'YAMAHA NMAX': 16500,
    'SUZUKI Yes 125': 14000,
    'DAFRA City 150': 9500,
    'KAWASAKI Ninja 300': 25000,
    'BMW GS': 35000,
}

# ============================================================
# TIPO DE LEILÃO — só aceita prefeituras
# ============================================================
PREFETURA_KEYWORDS = ['prefeitura', 'municipal', 'emdec', 'camara', 'pm ']
DETRAN_EXCLUDED = ['detran']

# ============================================================
# SCOUT AUTOMÁTICO
# ============================================================
SCOUT_SITES = {
    'sumare': {
        'nome': 'Sumare Leiloes',
        'url': 'https://www.sumareleiloes.com.br',
        'ativo': True,
        'frequencia_horas': 6,
    },
    'ricoleiloes': {
        'nome': 'Rico Leiloes',
        'url': 'https://www.ricoleiloes.com.br',
        'ativo': True,
        'frequencia_horas': 6,
    },
    'hastasp': {
        'nome': 'Hasta SP',
        'url': 'https://www.hastasp.com.br',
        'ativo': True,
        'frequencia_horas': 12,
    },
}

SCOUT_CRON = '0 */6 * * *'
MONITOR_CRON = '*/15 * * * *'

# ============================================================
# ALERTAS
# ============================================================
ALERTA_LANCE_PCT = 10   # reduziu de 15% para 10%
ALERTA_FASE_DISPUTA = True
ALERTA_NOVO_LOTE = True
EMAIL_TO = 'lucas170804@gmail.com'

# ============================================================
# LEILÕES AGENDADOS
# ============================================================
LEILOES_AGENDADOS = [
    {
        'id': 'itaoca_2027',
        'nome': 'Prefeitura Municipal de Itaoca',
        'site': 'ricoleiloes',
        'data_leilao': '2026-06-09',
        'data_abertura': '2026-06-01',
        'url': 'https://www.ricoleiloes.com.br/leiloes/2027',
        'status': 'agendado',
        'tipos': ['Veiculos Conservados (Com direito a documento)'],
    },
]