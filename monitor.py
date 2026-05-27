#!/usr/bin/env python3
"""
monitor.py — MotoBid v2.1
Verifica lotes ativos e gera dashboard. Roda a cada 15min via cron.

Fluxo:
  1. Carrega state.json
  2. Para cada lote nao encerrado, faz crawl e atualiza lance
  3. Detecta mudanca de fase (pre_leilao -> disputa -> encerrado)
  4. Dispara alerta se entrou em disputa
  5. Gera dashboard/index.html atualizado
"""
import os
from datetime import datetime
from crawlers import crawl_lote
from utils import log, carregar_json, salvar_json, fmt_brl
import smtplib
from email.mime.text import MIMEText
from config import EMAIL_TO, ALERTA_VARIACAO_PCT, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

STATE_FILE   = 'data/state.json'
HISTORY_FILE = 'data/history.json'
ALERTAS_FILE = 'data/alertas.json'
LOG_FILE     = 'data/monitor.log'
DASHBOARD    = 'dashboard/index.html'

def logf(msg):
    log(msg, LOG_FILE)

# ─────────────────────────────────────────────────────────
# HISTORICO
# ─────────────────────────────────────────────────────────
def add_historico(lid, dados):
    h = carregar_json(HISTORY_FILE, {})
    if lid not in h:
        h[lid] = []
    h[lid].append({'ts': datetime.now().isoformat(), **dados})
    h[lid] = h[lid][-50:]  # max 50 entradas por lote
    salvar_json(HISTORY_FILE, h)

# ─────────────────────────────────────────────────────────
# ALERTAS
# ─────────────────────────────────────────────────────────
def registrar_alerta(lid, tipo, msg, lot=None):
    alerts = carregar_json(ALERTAS_FILE, [])
    entry  = {
        'id':      f'{lid}_{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'lote_id': lid,
        'tipo':    tipo,
        'msg':     msg,
        'ts':      datetime.now().isoformat(),
        'lance':   lot.get('lance_atual') if lot else None,
    }
    alerts.insert(0, entry)
    salvar_json(ALERTAS_FILE, alerts[:100])
    enviar_alerta(entry)
    logf(f'ALERTA [{tipo}] {lid}: {msg}')

def enviar_alerta(entry):
    msg  = entry.get('msg', '')
    subj = f'[MotoBid] {entry.get("tipo","?")} — {entry.get("lote_id","")}'
    url  = 'https://lucas170804-2e459368-5214-vm.azure.gensparkclaw.com/motobid/'
    corpo = f'{msg}\n\nVer dashboard: {url}'
    # Email
    try:
        m = MIMEText(corpo, 'plain', 'utf-8')
        m['Subject'] = subj
        m['From']    = 'motobid@localhost'
        m['To']      = EMAIL_TO
        with smtplib.SMTP('localhost', 25, timeout=10) as s:
            s.sendmail('motobid@localhost', [EMAIL_TO], m.as_string())
    except:
        pass
    # Telegram
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            import urllib.request, urllib.parse
            url_tg = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
            data   = urllib.parse.urlencode({
                'chat_id': TELEGRAM_CHAT_ID,
                'text':    corpo,
            }).encode()
            urllib.request.urlopen(url_tg, data, timeout=10)
        except:
            pass

# ─────────────────────────────────────────────────────────
# MONITOR PRINCIPAL
# ─────────────────────────────────────────────────────────
def run():
    os.makedirs('data', exist_ok=True)
    os.makedirs('dashboard', exist_ok=True)
    logf('==== MONITOR ====')
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    state = carregar_json(STATE_FILE, {})

    if not state:
        logf('Nenhum lote. Rode auto_scout.py primeiro.')
        gerar_dashboard(state)
        return

    for lid, lot in state.items():
        if lot.get('fase') == 'encerrado':
            continue

        logf(f'  {lid}: verificando...')
        try:
            dados      = crawl_lote(lot)
            lance_ant  = lot.get('lance_atual', lot.get('lance_inicial', 0))
            lance_novo = dados.get('lance_atual', lance_ant)

            add_historico(lid, dados)

            lot['lance_atual'] = lance_novo
            lot['last_check']  = datetime.now().isoformat()
            lot['crawl_ok']    = dados.get('crawl_ok', False)

            # Encerrado?
            if dados.get('status') == 'encerrado':
                lot['fase'] = 'encerrado'
                registrar_alerta(
                    lid, 'encerrado',
                    f'{lot.get("modelo","")} encerrou — lance final {fmt_brl(lance_novo)}',
                    lot
                )

            # Entrou em disputa?
            elif lance_ant > 0 and lance_novo > lance_ant * (1 + ALERTA_VARIACAO_PCT / 100):
                fase_ant   = lot.get('fase')
                lot['fase'] = 'disputa'
                if fase_ant != 'disputa':
                    registrar_alerta(
                        lid, 'disputa',
                        f'🔥 {lot.get("modelo","")} entrou em DISPUTA!\n'
                        f'Lance: {fmt_brl(lance_novo)} (era {fmt_brl(lance_ant)})',
                        lot
                    )

            logf(f'  {lid} | {lot.get("modelo","?")} | '
                 f'{lot.get("fase","?")} | {fmt_brl(lance_novo)}')

        except Exception as e:
            logf(f'  {lid} ERRO: {e}')
            lot['last_error'] = str(e)

    salvar_json(STATE_FILE, state)
    gerar_dashboard(state)
    logf(f'OK — {len(state)} lotes verificados')

# ─────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────
def gerar_dashboard(state):
    now     = datetime.now().strftime('%d/%m/%Y %H:%M')
    alertas = carregar_json(ALERTAS_FILE, [])
    history = carregar_json(HISTORY_FILE, {})

    def lotes_cat(cat):
        return {
            k: v for k, v in state.items()
            if v.get('categoria', 'prefeitura') == cat
            and v.get('fase') != 'encerrado'
        }

    pref = lotes_cat('prefeitura')
    fin  = lotes_cat('financeira')
    sin  = lotes_cat('sinistro')

    def sparkline(lid):
        hist = history.get(lid, [])
        vals = [h.get('lance_atual', 0) for h in hist[-8:] if h.get('lance_atual')]
        if len(vals) < 2:
            return ''
        mx = max(vals) or 1
        bars = ''.join(
            f'<div style="width:5px;background:#ff5500;height:{max(3,int(v/mx*20))}px;'
            f'border-radius:2px;opacity:.7"></div>'
            for v in vals
        )
        return f'<div style="display:flex;align-items:flex-end;gap:2px;margin-top:8px;height:22px">{bars}</div>'

    def cards_html(lotes):
        if not lotes:
            return '<div style="color:#aaa;padding:24px;font-size:13px;text-align:center;">Nenhum lote nesta categoria ainda.</div>'
        html = '<div class="cards">'
        for lid, l in sorted(lotes.items(), key=lambda x: -x[1].get('score', 0)):
            lance  = l.get('lance_atual', 0)
            fipe   = l.get('fipe', 0)
            margem = l.get('margem_estimada', fipe - lance if fipe else 0)
            pct    = round((margem / fipe) * 100) if fipe else 0
            score  = l.get('score', 0)
            fase   = l.get('fase', 'pre_leilao')
            hi     = 'hi' if score >= 8.5 else ''
            fase_lbl = {
                'pre_leilao': 'Pré-leilão',
                'disputa':    'Disputa',
                'discovery':  'Discovery',
            }.get(fase, fase)
            fase_cls = 'ph-dis' if fase == 'disputa' else 'ph-pre'
            dbadge = (
                f'<div class="dbadge">{l.get("sinistro_tipo","Pequena monta")}</div>'
                if l.get('categoria') == 'sinistro' else ''
            )
            crawl_warn = (
                '<span style="color:#f59e0b;font-size:9px;"> ⚠ sem atualização</span>'
                if not l.get('crawl_ok') else ''
            )
            html += f"""
            <div class="card {hi}">
              <div class="ch">
                <div class="cid">LOTE {lid} · {str(l.get('leilao','?')).upper()}</div>
                <div class="cmod">{l.get('modelo','?')}</div>
                <div class="csub">
                  <span>{l.get('ano','')} · {l.get('cor','')} · Doc ✓</span>
                  <span class="ph {fase_cls}">{fase_lbl}</span>
                </div>
                {dbadge}
              </div>
              <div class="cb">
                <div class="sr">
                  <span class="sl">Score{crawl_warn}</span>
                  <span class="sv">{score}</span>
                </div>
                <div class="bb"><div class="bf" style="width:{score*10}%"></div></div>
                <div class="mets">
                  <div class="met"><div class="ml">Lance</div><div class="mv">R${int(lance):,}</div></div>
                  <div class="met"><div class="ml">FIPE est.</div><div class="mv">R${int(fipe):,}</div></div>
                  <div class="met"><div class="ml">Margem</div><div class="mv g">R${int(margem):,}</div></div>
                  <div class="met"><div class="ml">% FIPE</div><div class="mv o">{pct}%</div></div>
                </div>
                {sparkline(lid)}
              </div>
              <div class="cf">
                <span class="cplt">{l.get('site','?').upper()}</span>
                <a href="{l.get('url_lote','#')}" target="_blank" class="clnk">Ver lote ↗</a>
              </div>
            </div>"""
        html += '</div>'
        return html

    al_html = ''
    for a in alertas[:5]:
        ic = {'disputa':'🔥','encerrado':'✓','novo_lote':'★'}.get(a.get('tipo',''), '•')
        al_html += (
            f'<div class="al-item">'
            f'<span class="al-ts">{a.get("ts","")[:16]}</span> '
            f'{ic} {a.get("msg","")}'
            f'</div>'
        )
    if not al_html:
        al_html = '<div style="color:#aaa;padding:10px;font-size:12px;">Nenhum alerta ainda.</div>'

    tot    = sum(1 for v in state.values() if v.get('fase') != 'encerrado')
    margem = sum(v.get('margem_estimada', 0) for v in state.values() if v.get('fase') != 'encerrado')
    disp   = sum(1 for v in state.values() if v.get('fase') == 'disputa')
    avg_sc = round(sum(v.get('score', 0) for v in state.values() if v.get('fase') != 'encerrado') / max(tot, 1), 1)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="900">
<title>MotoBid</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700;800&family=Barlow+Condensed:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#f5f4f0;font-family:'Barlow',sans-serif;color:#1a1a1a;min-height:100vh;}}
.top{{background:#fff;border-bottom:1px solid #e8e6e0;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:10;}}
.logo-wrap{{display:flex;align-items:center;gap:11px;}}
.logo-box{{width:38px;height:38px;background:#ff5500;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:20px;}}
.logo-text{{font-family:'Barlow Condensed',sans-serif;font-size:24px;font-weight:800;color:#1a1a1a;letter-spacing:-.01em;}}
.logo-text span{{color:#ff5500;}}
.logo-sub{{font-size:10px;color:#aaa;font-family:'JetBrains Mono',monospace;margin-top:1px;}}
.top-right{{font-size:11px;color:#aaa;font-family:'JetBrains Mono',monospace;text-align:right;}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#e8e6e0;}}
.kpi{{background:#fff;padding:14px 20px;}}
.kpi-l{{font-size:10px;color:#aaa;font-family:'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;}}
.kpi-v{{font-family:'Barlow Condensed',sans-serif;font-size:28px;font-weight:800;color:#1a1a1a;}}
.kpi-s{{font-size:10px;margin-top:3px;color:#ff5500;font-weight:600;}}
.kpi-sn{{color:#aaa!important;}}
.scout{{background:#fff7f3;border-bottom:1px solid #fde0d0;padding:10px 24px;display:flex;align-items:center;gap:10px;font-size:12px;color:#888;}}
.pulse{{width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 5px #22c55e;flex-shrink:0;animation:pp 2s ease-in-out infinite;}}
@keyframes pp{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
.tabs{{display:flex;background:#fff;border-bottom:1px solid #e8e6e0;padding:0 24px;}}
.tab{{padding:12px 18px;font-size:12px;font-weight:700;cursor:pointer;color:#aaa;border-bottom:2px solid transparent;margin-bottom:-1px;display:flex;align-items:center;gap:7px;text-transform:uppercase;letter-spacing:.03em;transition:all .15s;user-select:none;}}
.tab:hover{{color:#666;}}
.tab.on{{color:#ff5500;border-bottom-color:#ff5500;}}
.tct{{font-size:10px;background:#f0ede8;color:#999;padding:1px 7px;border-radius:20px;font-family:'JetBrains Mono',monospace;font-weight:400;}}
.tab.on .tct{{background:#fff0e8;color:#ff5500;}}
.content{{padding:20px 24px;background:#f5f4f0;min-height:60vh;}}
.panel{{display:none;}}.panel.on{{display:block;}}
.sec-hd{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;}}
.sec-title{{display:flex;align-items:center;gap:10px;}}
.cat-badge{{font-size:10px;font-weight:700;padding:4px 10px;border-radius:4px;letter-spacing:.04em;text-transform:uppercase;}}
.cb-p{{background:#dcfce7;color:#15803d;}}
.cb-f{{background:#dbeafe;color:#1d4ed8;}}
.cb-s{{background:#fef9c3;color:#a16207;}}
.sec-sub{{font-size:11px;color:#aaa;font-family:'JetBrains Mono',monospace;}}
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:8px;}}
.card{{background:#fff;border:1px solid #e8e6e0;border-radius:10px;overflow:hidden;transition:border-color .15s,transform .15s;}}
.card:hover{{border-color:#ffb899;transform:translateY(-1px);}}
.card.hi{{border-left:3px solid #ff5500;border-color:#ffd4be;}}
.ch{{padding:12px 13px 10px;border-bottom:1px solid #f0ede8;}}
.cid{{font-size:9px;color:#bbb;font-family:'JetBrains Mono',monospace;margin-bottom:4px;}}
.cmod{{font-size:14px;font-weight:700;color:#1a1a1a;line-height:1.2;}}
.csub{{font-size:10px;color:#999;margin-top:3px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:3px;}}
.ph{{font-size:9px;font-weight:700;padding:2px 7px;border-radius:3px;text-transform:uppercase;letter-spacing:.04em;}}
.ph-pre{{background:#fef9c3;color:#a16207;}}
.ph-dis{{background:#fee2e2;color:#dc2626;}}
.dbadge{{font-size:9px;font-weight:700;padding:2px 8px;border-radius:3px;background:#fef3c7;color:#d97706;text-transform:uppercase;display:inline-block;margin-top:4px;}}
.cb{{padding:12px 13px;}}
.sr{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px;}}
.sl{{font-size:10px;color:#aaa;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}}
.sv{{font-family:'Barlow Condensed',sans-serif;font-size:22px;font-weight:800;color:#ff5500;}}
.bb{{height:2px;background:#f0ede8;border-radius:2px;margin-bottom:11px;}}
.bf{{height:2px;border-radius:2px;background:#ff5500;}}
.mets{{display:grid;grid-template-columns:1fr 1fr;gap:6px;}}
.met{{background:#f8f7f4;border-radius:6px;padding:7px 9px;}}
.ml{{font-size:9px;color:#aaa;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px;}}
.mv{{font-size:12px;font-weight:700;color:#1a1a1a;}}
.mv.g{{color:#16a34a;}}.mv.o{{color:#ff5500;}}
.cf{{padding:9px 13px;border-top:1px solid #f0ede8;display:flex;justify-content:space-between;align-items:center;}}
.cplt{{font-size:10px;color:#bbb;font-family:'JetBrains Mono',monospace;}}
.clnk{{font-size:10px;color:#ff5500;font-weight:600;text-decoration:none;}}
.clnk:hover{{text-decoration:underline;}}
.alerts-box{{background:#fff;border:1px solid #e8e6e0;border-radius:10px;padding:14px 16px;margin-top:20px;}}
.al-sec{{font-size:10px;color:#aaa;font-family:'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px;}}
.al-item{{padding:7px 0;border-bottom:1px solid #f0ede8;font-size:12px;color:#555;line-height:1.5;}}
.al-item:last-child{{border:none;}}
.al-ts{{color:#bbb;font-size:10px;font-family:'JetBrains Mono',monospace;margin-right:6px;}}
</style>
</head>
<body>
<div class="top">
  <div class="logo-wrap">
    <div class="logo-box">🏍</div>
    <div>
      <div class="logo-text">MOTO<span>BID</span></div>
      <div class="logo-sub">by minduca · monitor de leilões</div>
    </div>
  </div>
  <div class="top-right">
    {now}<br>
    atualiza em 15min
  </div>
</div>

<div class="kpis">
  <div class="kpi">
    <div class="kpi-l">Monitorados</div>
    <div class="kpi-v">{tot}</div>
    <div class="kpi-s">lotes ativos</div>
  </div>
  <div class="kpi">
    <div class="kpi-l">Margem total</div>
    <div class="kpi-v">R${int(margem/1000)}k</div>
    <div class="kpi-s">estimada</div>
  </div>
  <div class="kpi">
    <div class="kpi-l">Em disputa</div>
    <div class="kpi-v">{disp}</div>
    <div class="kpi-s {'kpi-sn' if disp == 0 else ''}">{'● ativo agora' if disp > 0 else 'monitorando'}</div>
  </div>
  <div class="kpi">
    <div class="kpi-l">Score médio</div>
    <div class="kpi-v">{avg_sc}</div>
    <div class="kpi-s kpi-sn">qualidade geral</div>
  </div>
</div>

<div class="scout">
  <div class="pulse"></div>
  <span>
    Sistema ativo · scout diário 07:00 · monitor a cada 15min ·
    <b style="color:#1a1a1a">{len(state)}</b> lotes no sistema ·
    <b style="color:#1a1a1a">34</b> plataformas monitoradas
  </span>
</div>

<div class="tabs">
  <div class="tab on" onclick="sw(this,'p')">🏛 Prefeitura <span class="tct">{len(pref)}</span></div>
  <div class="tab" onclick="sw(this,'f')">🏦 Financiamento <span class="tct">{len(fin)}</span></div>
  <div class="tab" onclick="sw(this,'s')">🔧 Sinistro <span class="tct">{len(sin)}</span></div>
</div>

<div class="content">
  <div class="panel on" id="pp">
    <div class="sec-hd">
      <div class="sec-title">
        <span class="cat-badge cb-p">🏛 Prefeitura</span>
        <span class="sec-sub">lance R$500–R$6k · doc obrigatório</span>
      </div>
    </div>
    {cards_html(pref)}
  </div>
  <div class="panel" id="pf">
    <div class="sec-hd">
      <div class="sec-title">
        <span class="cat-badge cb-f">🏦 Financiamento</span>
        <span class="sec-sub">lance R$5k–R$25k · recuperação de crédito</span>
      </div>
    </div>
    {cards_html(fin)}
  </div>
  <div class="panel" id="ps">
    <div class="sec-hd">
      <div class="sec-title">
        <span class="cat-badge cb-s">🔧 Sinistro</span>
        <span class="sec-sub">só pequena monta · doc obrigatório · margem mín. R$3.500</span>
      </div>
    </div>
    {cards_html(sin)}
  </div>
  <div class="alerts-box">
    <div class="al-sec">Últimos alertas</div>
    {al_html}
  </div>
</div>

<script>
function sw(el,p){{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(x=>x.classList.remove('on'));
  el.classList.add('on');
  document.getElementById('p'+p).classList.add('on');
}}
</script>
</body>
</html>"""

    with open(DASHBOARD, 'w', encoding='utf-8') as f:
        f.write(html)
    logf(f'Dashboard gerado: {DASHBOARD}')

if __name__ == '__main__':
    run()   