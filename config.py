#!/usr/bin/env python3
'''
CONFIG — MotoBid
Filtros e thresholds para análise de lotes de leilão
'''

# ============================================================
# RANKING DE MARCAS (por potencial de revenda)
# ============================================================
# Tier 1 — TOP: mais demandadas no Brasil, vendem rápido
TIER_TOP = ['HONDA', 'YAMAHA']

# Tier 2 — Alta: boa demanda, margem interessante
TIER_HIGH = ['SUZUKI', 'DAFRA', 'KAWASAKI', 'BMW']

# Tier 3 — Outras: aceita se margem for boa
TIER_OTHER = ['KASINSKI', 'KTM', 'APRILIA', 'ROYAL ENFIELD', 'BAJAJ', 'HAOJUE']

# Excluir: marca sem mercado de peças / revenda difícil
EXCLUDED = ['SHINERAY', 'SUCATA', 'MOTOR INSERVIDO']

# ============================================================
# THRESHOLDS
# ============================================================
# Margem mínima por tier
MARGEM_MIN_TIER1 = 2000  # Honda, Yamaha
MARGEM_MIN_TIER2 = 3000  # Suzuki, Dafra, Kawasaki, BMW
MARGEM_MIN_TIER3 = 4000  # Outras

LANCE_MINIMO = 500
LANCE_MAXIMO = 100000

# Score mínimo pra entrar no monitoramento
SCORE_MINIMO = 5.0

# ============================================================
# DOCUMENTO
# ============================================================
DOC_KEYWORDS = [
    'com direito a documento', 'para circular', 'documento ok',
    'documento original', 'ipva ok', 'licenciado', 'documentacao ok',
    'placa verde', 'veiculo conservado'
]

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
ALERTA_LANCE_PCT = 15
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