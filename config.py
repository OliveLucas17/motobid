#!/usr/bin/env python3
'''
CONFIG — MotoBid
'''

BRANDAS_EXCLUIDAS = ['honda', 'yamaha', 'shineray']
MARGEM_MINIMA = 3000
LANCE_MINIMO = 500
LANCE_MAXIMO = 100000

# Sites para scout automático
SCOUT_SITES = {
    'sumare': {
        'url': 'https://www.sumareleiloes.com.br',
        'ativo': True,
        'frequencia_horas': 6,
    },
    'ricoleiloes': {
        'url': 'https://www.ricoleiloes.com.br',
        'ativo': True,
        'frequencia_horas': 6,
    },
    'hastasp': {
        'url': 'https://www.hastasp.com.br',
        'ativo': True,
        'frequencia_horas': 12,
    },
}

# Lotes já adicionados manualmente
LOTES_MANUAL = [
    {
        'id': '0054',
        'leilao': '5105',
        'leiloeiro': 'Prefeitura Vinhedo',
        'site': 'sumare',
        'modelo': 'Honda CG 160 Start',
        'ano': '24/24',
        'cor': 'Vermelho',
        'fase': 'pre_leilao',
        'url_lote': 'https://www.sumareleiloes.com.br/lotes/a2d784ba-42d8-4364-8d70-5df8f9a3e852',
        'url_leilao': 'https://www.sumareleiloes.com.br/leiloes/5105',
        'lance_inicial': 5800.0,
        'fipe': 16322.0,
        'margem_estimada': 10522.0,
        'documento': 'Com direito a documento',
    },
]

# Leilao agendado — Prefeitura Itaoca (Ricoleiloes)
LEILOES_AGENDADOS = [
    {
        'id': 'itaoca_2027',
        'nome': 'Prefeitura Municipal de Itaoca',
        'site': 'ricoleiloes',
        'data_leilao': '2026-06-09',
        'data_abertura_lances': '2026-06-01',
        'url': 'https://www.ricoleiloes.com.br/leiloes/2027',
        'status': 'agendado',
        'tipos': ['Veículos Conservados (Com direito a documento)'],
    },
]

# Thresholds de alerta
ALERTA_LANCE_PCT = 15  # % de mudança no lance pra notificar
ALERTA_FASE_DISPUTA = True
ALERTA_NOVO_LOTE = True

# Frequência do scout
SCOUT_CRON = '0 */6 * * *'  # a cada 6h
MONITOR_CRON = '*/15 * * * *'  # a cada 15min

# Email
EMAIL_TO = 'lucas170804@gmail.com'