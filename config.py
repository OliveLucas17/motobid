#!/usr/bin/env python3
"""config.py — MotoBid v2.1 — regras de negocio."""

# ─────────────────────────────────────────────────────────
# TIERS DE MARCA
# ─────────────────────────────────────────────────────────
TIER_TOP    = ['HONDA', 'YAMAHA']
TIER_ALTA   = ['SUZUKI', 'KAWASAKI', 'BMW', 'DAFRA']
TIER_OUTRAS = ['SHINERAY', 'KTM', 'KASINSKI', 'APRILIA', 'BAJAJ', 'HAOJUE', 'ROYAL ENFIELD']
EXCLUIDAS   = []
# Modelos de carro — categorizados em section futura
MODELOS_CARRO = [
    'FIT','CIVIC','CITY','HRV','CRV','WRV',
    'COROLLA','ETIOS','YARIS','HILUX','CAMRY',
    'GOL','POLO','VOYAGE','FOX','SAVEIRO','GOLF','TIGUAN',
    'UNO','PALIO','SIENA','PUNTO','DOBLO','FIORINO','TORO','STRADA',
    'ONIX','PRISMA','CELTA','CORSA','VECTRA','CRUZE','TRACKER','COBALT',
    'FIESTA','KA','FOCUS','ECOSPORT','RANGER','FUSION','EDGE',
    'MONZA','ESCORT','ASTRA','ZAFIRA','MERIVA',
    'SANDERO','DUSTER','LOGAN','STEPWAY',
    'COMPASS','RENEGADE','CHEROKEE',
]

# ─────────────────────────────────────────────────────────
# MARGENS MÍNIMAS POR TIER E CATEGORIA
# ─────────────────────────────────────────────────────────
MARGEM_MIN = {
    'prefeitura': {'TOP': 1500, 'ALTA': 2500, 'OUTRAS': 4000},
    'financeira':  {'TOP': 1500, 'ALTA': 2500, 'OUTRAS': 4000},
    'sinistro':    {'TOP': 3500, 'ALTA': 3500, 'OUTRAS': 3500},
}

TICKET_IDEAL = {
    'prefeitura': (500,   6000),
    'financeira':  (5000, 25000),
    'sinistro':    (3000, 20000),
}

# ─────────────────────────────────────────────────────────
# FILTROS GERAIS
# ─────────────────────────────────────────────────────────
ANO_MINIMO   = 2010
LANCE_MINIMO = 500
LANCE_MAXIMO = 80000
SCORE_MINIMO = 5.0

# ─────────────────────────────────────────────────────────
# DOCUMENTO — obrigatorio sem excecao
# ─────────────────────────────────────────────────────────
DOC_OK_KEYWORDS = [
    'com direito a documento', 'para circular', 'documento ok',
    'ipva ok', 'licenciado', 'documentacao ok',
    'veiculo conservado', 'com documento', 'placa',
]
SUCATA_KEYWORDS = [
    'sucata', 'sem documento', 'sem direito a documento',
    'motor inservivel', 'para pecas', 'nao circula', 'baixado',
]

# ─────────────────────────────────────────────────────────
# SINISTRO — classificacoes aceitas
# ─────────────────────────────────────────────────────────
SINISTRO_ACEITO    = ['pequena monta']
SINISTRO_REJEITADO = ['media monta', 'perda total', 'colisao grave']

# ─────────────────────────────────────────────────────────
# DETECÇÃO AUTOMÁTICA DE CATEGORIA
# O scout le o texto do leilao e detecta o tipo automaticamente
# ─────────────────────────────────────────────────────────
CATEGORIA_KEYWORDS = {
    'prefeitura': [
        'prefeitura municipal',
        'prefeitura de',
        'municipio de',
        'poder publico',
        'patrimonio publico',
        'bens publicos',
        'secretaria municipal',
        'detran',
        'denatran',
        'orgao publico',
        'leilao publico',
    ],
    'financeira': [
        'alienacao fiduciaria',
        'retomada',
        'bv financeira',
        'santander',
        'itau',
        'bradesco',
        'caixa economica',
        'banco do brasil',
        'banco bradesco',
        'recuperacao de credito',
        'inadimplencia',
        'devedor fiduciante',
        'credor fiduciario',
        'busca e apreensao',
        'financiamento',
    ],
    'sinistro': [
        'pequena monta',
        'media monta',
        'perda total',
        'sinistro',
        'porto seguro',
        'bradesco seguros',
        'suhai',
        'tokio marine',
        'hdl seguros',
        'colisao',
        'indenizado',
        'sucata autorizada',
        'veiculo sinistrado',
    ],
}

def detectar_categoria(texto):
    """Detecta categoria do leilao pelo texto.
    Retorna 'prefeitura', 'financeira' ou 'sinistro'.
    Default: 'prefeitura' quando nao identificado.
    """
    tl = texto.lower()
    scores = {cat: 0 for cat in CATEGORIA_KEYWORDS}
    for cat, keywords in CATEGORIA_KEYWORDS.items():
        for kw in keywords:
            if kw in tl:
                scores[cat] += 1
    melhor = max(scores, key=scores.get)
    return melhor if scores[melhor] > 0 else 'None'

# ─────────────────────────────────────────────────────────
# PLATAFORMAS — leiloeiros oficiais SP
# categoria=None pois e detectada automaticamente pelo scout
# ─────────────────────────────────────────────────────────
PLATAFORMAS_SP = {
    'hastapublica': {
        'leiloeiro': 'Marcelo Valland',
        'url':       'https://www.hastapublica.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'liderleiloes': {
        'leiloeiro': 'Caroline de Souza Ribas',
        'url':       'https://liderleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'sodresantoro': {
        'leiloeiro': 'Flávio Cunha Sodré Santoro',
        'url':       'https://www.sodresantoro.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'leiloei': {
        'leiloeiro': 'Felipe Nunes Gomes Teixeira Bignardi',
        'url':       'https://www.leiloei.com/',
        'categoria': None,
        'ativo':     True,
    },
    'willianleiloes': {
        'leiloeiro': 'Willian Augusto Ferreira De Araújo',
        'url':       'https://www.willianleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'sfrazao': {
        'leiloeiro': 'Victor Alberto Severino Frazão',
        'url':       'https://www.sfrazao.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'gaialeiloes': {
        'leiloeiro': 'Priscila Da Silva Jordão',
        'url':       'https://www.gaialeiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'bidmax': {
        'leiloeiro': 'Ligia Seixas',
        'url':       'https://www.bidmax.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'picellileiloes': {
        'leiloeiro': 'Joel Augusto Picelli Filho',
        'url':       'https://www.picellileiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'globoleiloes': {
        'leiloeiro': 'Cassia Negrete Nunes Balbino',
        'url':       'https://www.globoleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'megavaleleiloes': {
        'leiloeiro': 'Jeter De Oliveira Záccaro',
        'url':       'https://www.megavaleleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'superdiasleiloes': {
        'leiloeiro': 'José Luis Gonçalves Dias',
        'url':       'https://www.superdiasleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'clebercardoso': {
        'leiloeiro': 'Cleber Cardoso Pereira',
        'url':       'https://www.clebercardosoleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'giordanoleiloes': {
        'leiloeiro': 'Giordano Bruno Coan Amador',
        'url':       'https://www.giordanoleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'alienajud': {
        'leiloeiro': 'Mauro Da Cruz',
        'url':       'https://www.alienajud.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'lancenow': {
        'leiloeiro': 'Guilherme Valland Junior',
        'url':       'https://www.lancenow.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'ktzleiloes': {
        'leiloeiro': 'Vivian Thomaz Katzenelson',
        'url':       'https://www.ktzleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'amaralleiloes': {
        'leiloeiro': 'Eder Amaral De Oliveira',
        'url':       'https://www.amaralleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'leilaooficialonline': {
        'leiloeiro': 'Clecio Oliveira de Carvalho',
        'url':       'https://www.leilaooficialonline.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'albertomacedo': {
        'leiloeiro': 'Alberto Jose Marchi Macedo',
        'url':       'https://www.albertomacedoleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'centraljudicial': {
        'leiloeiro': 'Andre Sobreira Da Silva',
        'url':       'https://www.centraljudicial.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'superbid': {
        'leiloeiro': 'Alexandre Travassos',
        'url':       'https://www.superbid.net/',
        'categoria': None,
        'ativo':     True,
    },
    'uonleiloes': {
        'leiloeiro': 'Fernando Domingues De Oliveira Jr',
        'url':       'https://www.uonleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'cunhaleiloeiro': {
        'leiloeiro': 'Hugo Leonardo Alvarenga Cunha',
        'url':       'https://www.cunhaleiloeiro.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'crisleiloes': {
        'leiloeiro': 'Cristiane Franklin Simões',
        'url':       'https://www.crisleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'domingosleiloes': {
        'leiloeiro': 'Domingos Valter Sammarco Sobrinho',
        'url':       'https://www.domingosleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'fidalgoleiloes': {
        'leiloeiro': 'Douglas José Fidalgo',
        'url':       'https://www.fidalgoleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'lanceleiloes': {
        'leiloeiro': 'Aedi de Andrade Verrone',
        'url':       'https://www.lanceleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'tahaleiloes': {
        'leiloeiro': 'Ahmid Hussein Ibrahin Taha',
        'url':       'https://www.tahaleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'vivaleiloes': {
        'leiloeiro': 'Alethea Carvalho Lopes',
        'url':       'https://www.vivaleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'leilaoonline': {
        'leiloeiro': 'Eduardo Jordao Boyadjian',
        'url':       'https://www.leilaoonline.net/',
        'categoria': None,
        'ativo':     True,
    },
    'sumareleiloes': {
        'leiloeiro': 'Sumaré Leilões',
        'url':       'https://www.sumareleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'ricoleiloes': {
        'leiloeiro': 'Rico Leilões',
        'url':       'https://www.ricoleiloes.com.br/',
        'categoria': None,
        'ativo':     True,
    },
    'hastasp': {
        'leiloeiro': 'Hasta SP',
        'url':       'https://www.hastasp.com.br/',
        'categoria': None,
        'ativo':     True,
    },
}

# Plataformas SPA — gsk nao consegue crawlar diretamente
# Usam apenas gsk search para encontrar lotes especificos
PLATAFORMAS_SPA = {
    'superbid', 'vivaleiloes', 'leilaoonline',
    'bidmax', 'lancenow',
}

# Plataformas que funcionam bem com crawl direto
PLATAFORMAS_CRAWL = {
    'hastapublica', 'liderleiloes', 'sodresantoro',
    'sfrazao', 'alienajud', 'amaralleiloes',
    'lanceleiloes', 'crisleiloes', 'ktzleiloes',
}

# Leiloes conhecidos do Sumare — varredura direta por ID
LEILOES_SUMARE = {
    '5105': 'Prefeitura Vinhedo',
    '1905': 'Sumaré — 51 lotes',
    '2511': 'Sumaré — 45 lotes',
    '2530': 'Sumaré', '3174': 'Sumaré',
    '3200': 'Sumaré', '3411': 'Sumaré',
}
URL_SUMARE_LEILAO = 'https://www.sumareleiloes.com.br/leiloes/{id}'

LEILOES_RICO = {
    '2027': {
        'nome': 'Prefeitura Itaoca',
        'data_leilao': '2026-06-09',
        'url': 'https://www.ricoleiloes.com.br/leiloes/2027',
    }
}

# ─────────────────────────────────────────────────────────
# TABELA DE PREÇOS — FB Marketplace Brasil 2026
# ─────────────────────────────────────────────────────────
PRECOS_REF = {
    'HONDA CG 160 START': 16500, 'HONDA CG 160 FAN': 15500,
    'HONDA CG 160 TITAN': 16000, 'HONDA CG 150 TITAN': 12000,
    'HONDA CG 125 FAN': 9000,    'HONDA CG 125 TODAY': 7500,
    'HONDA BIZ 125': 11500,      'HONDA BIZ 110': 9000,
    'HONDA POP 110': 10000,      'HONDA PCX 150': 17500,
    'HONDA PCX 160': 19000,      'HONDA CB 300R': 20000,
    'HONDA XRE 190': 19000,      'HONDA XRE 300': 23000,
    'HONDA BROS 160': 15500,     'HONDA TWISTER 250': 18000,
    'YAMAHA FACTOR 150': 13500,  'YAMAHA FAZER 250': 16500,
    'YAMAHA YBR 125': 10000,     'YAMAHA CRYPTON 110': 10500,
    'YAMAHA XTZ 125': 11000,     'YAMAHA XTZ 250': 16500,
    'YAMAHA LANDER 250': 17000,  'YAMAHA NMAX 160': 18000,
    'YAMAHA NMAX 160 ABS': 20000,'YAMAHA TENERE 250': 24000,
    'YAMAHA MT 03': 25000,
    'SUZUKI YES 125': 13000,     'SUZUKI BURGMAN 200': 17000,
    'KAWASAKI NINJA 300': 26000, 'KAWASAKI NINJA 400': 30000,
    'KAWASAKI Z 400': 28000,     'DAFRA CITY 150': 9500,
    'BMW G310R': 24000,          'BMW G310GS': 26000,
    'SHINERAY XY 125': 6500,
}
PRECO_FALLBACK = {
    'HONDA': 13000, 'YAMAHA': 12000, 'SUZUKI': 11000,
    'KAWASAKI': 15000, 'DAFRA': 8000, 'BMW': 20000, 'SHINERAY': 5500,
}

# ─────────────────────────────────────────────────────────
# SCORE
# ─────────────────────────────────────────────────────────
SCORE_PESOS = {
    'tier_top': 10, 'tier_alta': 8, 'tier_outras': 6,
    'doc_ok': 2, 'margem_bonus': 3, 'ano_2020': 1.5, 'ano_2015': 0.5,
}

# ─────────────────────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────────────────────
ALERTA_VARIACAO_PCT = 10
EMAIL_TO         = 'lucas170804@gmail.com'
TELEGRAM_TOKEN   = ''
TELEGRAM_CHAT_ID = ''

CRON_SCOUT   = '0 7 * * *'
CRON_MONITOR = '*/15 * * * *'       