#!/usr/bin/env python3
import subprocess, json, os, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from crawlers import crawl

STATE_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/state.json'
HISTORY_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/history.json'
ALERTAS_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/alertas.json'
LOG_FILE = '/home/work/.openclaw/workspace/projects/motobid/data/monitor.log'

def log(msg):
    ts = datetime.now().strftime('%d/%m %H:%M')
    line = '[' + ts + '] ' + msg
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_history(lote_id, data):
    history = load_history()
    if lote_id not in history:
        history[lote_id] = []
    history[lote_id].append({'ts': datetime.now().isoformat(), **data})
    history[lote_id] = history[lote_id][-100:]
    save_history(history)

def alert(lote_id, tipo, msg, lot_data=None):
    alerts = []
    if os.path.exists(ALERTAS_FILE):
        try:
            with open(ALERTAS_FILE) as f:
                alerts = json.load(f)
        except:
            alerts = []
    
    entry = {
        'id': lote_id + '_' + datetime.now().strftime('%Y%m%d%H%M%S'),
        'lote_id': lote_id,
        'tipo': tipo,
        'msg': msg,
        'ts': datetime.now().isoformat(),
        'lance': lot_data.get('lance_atual') if lot_data else None,
    }
    alerts.insert(0, entry)
    alerts = alerts[:100]
    
    with open(ALERTAS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)
    
    send_alert_email(entry)
    log('ALERTA [' + tipo + '] ' + lote_id + ': ' + msg)

def send_alert_email(entry):
    try:
        msg = MIMEMultipart('alternative')
        tipo = entry.get('tipo', '')
        emoji_map = {'disputa': 'FOGO', 'lance_change': 'DOLLAR', 'novo_lote': 'NEW', 'encerrado': 'OK'}
        tipo_nome = {'disputa': 'Disputa', 'lance_change': 'Lance atualizado', 'novo_lote': 'Novo lote', 'encerrado': 'Encerrado'}
        emoji = emoji_map.get(tipo, 'BELL')
        
        subj = '[' + emoji + '] [MotoBid] ' + tipo_nome.get(tipo, tipo) + ' - ' + entry.get('lote_id', '')
        body = '[' + datetime.now().strftime('%d/%m %H:%M') + '] ' + entry.get('msg', '') + '\n\nAcesse: https://lucas170804-2e459368-5214-vm.azure.gensparkclaw.com/motobid/\n\n---\nMotoBid - AlfaPrime Transportes\n'
        
        msg['Subject'] = subj
        msg['From'] = 'motobid@alfaemail.com'
        msg['To'] = 'lucas170804@gmail.com'
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('localhost', 25, timeout=10) as s:
            s.sendmail('motobid@alfaemail.com', ['lucas170804@gmail.com'], msg.as_string())
        log('Email enviado')
    except Exception as e:
        log('Erro email: ' + str(e))

def fase_label(fase):
    labels = {
        'discovery': 'Descoberta',
        'pre_leilao': 'Pre-Leilao',
        'disputa': 'DISPUTA',
        'encerrado': 'Encerrado',
    }
    return labels.get(fase, fase)

def run():
    os.makedirs('/home/work/.openclaw/workspace/projects/motobid/data', exist_ok=True)
    log('============================')
    log('MOTOBD MONITOR')
    
    state = load_state()
    if not state:
        log('Nenhum lote cadastrado. Rode auto_scout.py primeiro.')
        return
    
    for lote_id, lot in state.items():
        if lot.get('fase') == 'encerrado':
            continue
        
        log('  ' + lote_id + ': verificando...')
        
        try:
            data = crawl(lot)
            add_history(lote_id, data)
            
            lance_antigo = lot.get('lance_atual', lot.get('lance_inicial', 0))
            lance_novo = data.get('lance_atual', lance_antigo)
            
            lot['lance_atual'] = lance_novo
            lot['status'] = data.get('status', lot.get('status'))
            lot['last_check'] = datetime.now().isoformat()
            
            fase_antiga = lot.get('fase', 'pre_leilao')
            
            if data.get('status') == 'encerrado':
                lot['fase'] = 'encerrado'
                alert(lote_id, 'encerrado', lot.get('modelo', '') + ' encerrou em R$ ' + str(lance_novo), lot)
            elif lance_novo > lance_antigo * 1.15 and lance_antigo > 0:
                lot['fase'] = 'disputa'
                if fase_antiga != 'disputa':
                    alert(lote_id, 'disputa', lot.get('modelo', '') + ' entrou em DISPUTA! Lance: R$ ' + str(lance_novo), lot)
                else:
                    alert(lote_id, 'lance_change', lot.get('modelo', '') + ' nova alta: R$ ' + str(lance_novo), lot)
            
            modelo = lot.get('modelo', '?')
            fase = fase_label(lot.get('fase', '?'))
            lance_str = 'R$ ' + str(round(lance_novo, 2))
            log('  ' + lote_id + ' | ' + modelo + ' | fase=' + fase + ' | lance=' + lance_str)
            
        except Exception as e:
            log('  ' + lote_id + ' ERRO: ' + str(e))
            lot['last_error'] = str(e)
    
    save_state(state)
    generate_dashboard(state)
    log('OK - ' + str(len(state)) + ' lotes verificados')

def generate_dashboard(state):
    history = load_history()
    
    fase_colors = {
        'discovery': '#8b5cf6',
        'pre_leilao': '#3b82f6',
        'disputa': '#ff6b35',
        'encerrado': '#10b981',
    }
    
    cards_html = ''
    for lote_id, lot in state.items():
        color = fase_colors.get(lot.get('fase', ''), '#888')
        lance = lot.get('lance_atual', 0)
        fipe = lot.get('fipe', 0)
        margem = fipe - lance if fipe else 0
        score = min(10, round((margem / 5000) * 7, 1)) if margem > 0 else 0
        
        price_history = ''
        if lote_id in history and len(history[lote_id]) > 1:
            prices = [h.get('lance_atual', 0) for h in history[lote_id] if h.get('lance_atual')]
            if prices and len(prices) > 1:
                bars = ''.join(['<div style=\"height:6px;background:' + color + ';width:' + str(round((i+1)/len(prices)*100)) + '%;margin:1px 0;border-radius:2px;opacity:0.6\"></div>' for i in range(len(prices))])
                price_history = '<div style=\"margin-top:8px;padding:4px 8px;background:#0a0a1a;border-radius:6px\">' + bars + '</div>'
        
        url = lot.get('url_lote', '#')
        cards_html += '<div class=\"card\"><div class=\"card-header\"><span class=\"card-id\">LOTE ' + lote_id.upper() + '</span><span class=\"card-fase\" style=\"background:' + color + ';color:white\">' + fase_label(lot.get('fase', '?')) + '</span></div><div class=\"card-modelo\">' + str(lot.get('modelo', '?')) + ' <span class=\"card-ano\">' + str(lot.get('ano', '')) + '</span></div><div class=\"card-cor\">' + str(lot.get('cor', '')) + ' | ' + str(lot.get('marca', '')) + '</div><div class=\"score-bar\"><div class=\"score-fill\" style=\"width:' + str(int(score*10)) + '%;background:' + color + '\"></div></div><div class=\"score-label\">score ' + str(score) + '/10 | margem R$ ' + str(int(margem)) + '</div><div class=\"metrics\"><div class=\"metric-row\"><span>Lance atual</span><span class=\"val\" style=\"color:' + color + '\">R$ ' + str(round(lance, 2)) + '</span></div><div class=\"metric-row\"><span>FIPE estimado</span><span class=\"val\">R$ ' + str(round(fipe, 2)) + '</span></div><div class=\"metric-row\"><span>Margem</span><span class=\"val green\">R$ ' + str(round(margem, 2)) + '</span></div></div>' + price_history + '<a href=\"' + url + '\" target=\"_blank\" class=\"card-btn\">Ver no Leilao</a></div>'
    
    alerts_html = ''
    if os.path.exists(ALERTAS_FILE):
        try:
            with open(ALERTAS_FILE) as f:
                alerts_data = json.load(f)
            for a in alerts_data[:5]:
                ts = a.get('ts', '')[:16]
                emoji_map = {'disputa': '🔥', 'lance_change': '💰', 'novo_lote': '🆕', 'encerrado': '✅'}
                e = emoji_map.get(a.get('tipo'), '📢')
                alerts_html += '<div class=\"alert-item\"><span class=\"alert-ts\">' + ts + '</span> ' + e + ' ' + str(a.get('msg', '')) + '</div>'
        except:
            pass
    
    discovery = sum(1 for v in state.values() if v.get('fase') == 'discovery')
    pre_leilao = sum(1 for v in state.values() if v.get('fase') == 'pre_leilao')
    disputa = sum(1 for v in state.values() if v.get('fase') == 'disputa')
    encerrado = sum(1 for v in state.values() if v.get('fase') == 'encerrado')
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    html = '<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\"><title>MotoBid</title><style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:Inter,-apple-system,sans-serif;background:#0a0a1a;color:#e0e0e0;min-height:100vh}.header{background:linear-gradient(135deg,#ff6b35,#1a1a2e);padding:22px 36px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}.logo{font-size:26pt;font-weight:900;color:white}.logo span{color:#ff6b35}.logo small{font-size:10pt;color:rgba(255,255,255,0.6);font-weight:400;display:block;margin-top:2px}.header-right{text-align:right}.time{font-size:11pt;color:rgba(255,255,255,0.7)}.status{font-size:10pt;color:#10b981;font-weight:600;margin-top:2px}.content{padding:24px 36px;max-width:1300px;margin:0 auto}.fases-bar{display:flex;gap:10px;margin-bottom:22px;flex-wrap:wrap}.fase-chip{padding:7px 16px;border-radius:20px;font-size:11pt;font-weight:600}.fase-discovery{background:#2d1f6b;color:#a78bfa}.fase-pre_leilao{background:#1e3a6b;color:#60a5fa}.fase-disputa{background:#3d1a00;color:#ff6b35}.fase-encerrado{background:#0d2d1d;color:#34d399}.section-title{font-size:11pt;color:#666;margin-bottom:14px;margin-top:26px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #1e2a4a;padding-bottom:8px}.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px}.card{background:#12122a;border-radius:14px;padding:20px;border:1.5px solid #1e2a4a;transition:transform .2s,border-color .2s}.card:hover{transform:translateY(-3px);border-color:#ff6b35}.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.card-id{font-size:9pt;color:#ff6b35;font-weight:700;text-transform:uppercase;letter-spacing:1px}.card-fase{font-size:9pt;font-weight:700;padding:3px 10px;border-radius:10px}.card-modelo{font-size:15pt;font-weight:800;color:white}.card-ano{font-weight:400;color:#888;font-size:12pt}.card-cor{font-size:11pt;color:#555;margin-top:3px}.score-bar{height:4px;background:#1e2a4a;border-radius:3px;margin:12px 0 6px;overflow:hidden}.score-fill{height:100%;border-radius:3px;transition:width .5s}.score-label{font-size:10pt;color:#666;margin-bottom:10px}.metrics{border-top:1px solid #1e2a4a;padding-top:10px}.metric-row{display:flex;justify-content:space-between;padding:5px 0;font-size:11pt}.metric-row span:first-child{color:#555}.metric-row .val{font-weight:700;color:white}.metric-row .val.green{color:#10b981}.card-btn{display:block;text-align:center;margin-top:14px;padding:9px;background:#1e2a4a;color:#60a5fa;border-radius:8px;text-decoration:none;font-size:10pt;font-weight:600}.card-btn:hover{background:#ff6b35;color:white}.alerts{background:#12122a;border-radius:12px;padding:16px 20px;margin-top:4px}.alert-item{padding:8px 0;border-bottom:1px solid #1e2a4a;font-size:11pt}.alert-item:last-child{border:none}.alert-ts{color:#555;font-size:10pt;margin-right:8px}.scout-banner{background:linear-gradient(135deg,#1e3a2a,#0a1a1a);border:1px solid #10b981;border-radius:12px;padding:16px 20px;margin-bottom:20px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}.scout-banner .badge{background:#10b981;color:white;padding:4px 12px;border-radius:10px;font-size:10pt;font-weight:700;white-space:nowrap}.scout-banner p{color:#888;font-size:12pt;flex:1}.scout-banner strong{color:#10b981}.footer{text-align:center;padding:20px;font-size:10pt;color:#333;border-top:1px solid #1e2a4a;margin-top:30px}@media(max-width:700px){.header{padding:16px 20px}.content{padding:16px 20px}}</style></head><body><div class=header><div class=logo>Moto<span>Bid</span><small>alerta inteligente | AlfaPrime Transportes</small></div><div class=header-right><div class=time>' + now + '</div><div class=status>● Monitor ativo</div></div></div><div class=content><div class=scout-banner><span class=badge>SCOUT ATIVO</span><p>Auto-scout a cada 6h. <strong>Prefeitura Itaoca</strong> - Leilao 09/06/2026. Filtro: SEM Honda/Yamaha/Shineray, COM documento, margem &gt;R$3k.</p></div><div class=fases-bar><div class=fase-chip fase-discovery>Descoberta (' + str(discovery) + ')</div><div class=fase-chip fase-pre_leilao>Pre-Leilao (' + str(pre_leilao) + ')</div><div class=fase-chip fase-disputa>DISPUTA (' + str(disputa) + ')</div><div class=fase-chip fase-encerrado>Encerrado (' + str(encerrado) + ')</div></div><div class=section-title>Lotes monitorados (' + str(len(state)) + ')</div><div class=card-grid>' + (cards_html if cards_html else '<p style=color:#555;font-size:12pt;padding:20px 0>Nenhum lote. Rode auto_scout.py para comecar.</p>') + '</div><div class=section-title>Ultimos alertas</div><div class=alerts>' + (alerts_html if alerts_html else '<p style=color:#444;font-size:11pt;padding:10px 0>Nenhum alerta ainda.</p>') + '</div></div><div class=footer>MotoBid | AlfaPrime Transportes | Atualiza a cada 15 min</div></body></html>'
    
    out = '/home/work/.openclaw/workspace/projects/motobid/dashboard/index.html'
    with open(out, 'w') as f:
        f.write(html)
    
    os.makedirs('/home/work/.openclaw/workspace/projects/motobid/dashboard', exist_ok=True)
    with open('/home/work/.openclaw/workspace/projects/motobid/dashboard/index.html', 'w') as f:
        f.write(html)

if __name__ == '__main__':
    run()
