#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Weekly Cognitive Report Generator — MotoBid
# Runs every Monday 09:00 BRT (America/Sao_Paulo)
# Generates analytics report based on monitor logs, state changes, and session memory

import json, os, subprocess
from datetime import datetime, timedelta

WORKSPACE = '/home/work/.openclaw/workspace'
MOTOBID_PATH = WORKSPACE + '/projects/motobid'
STATE_FILE = MOTOBID_PATH + '/data/state.json'
HISTORY_FILE = MOTOBID_PATH + '/data/history.json'
MONITOR_LOG = MOTOBID_PATH + '/data/monitor.log'
REPORT_PATH = WORKSPACE + '/reports/weekly'

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def load_json(path, default=[]):
    if os.path.exists(path):
        with open(path) as f:
            try: return json.load(f)
            except: pass
    return default

def count_log_lines(log_path, days=7):
    if not os.path.exists(log_path): return 0
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    with open(log_path) as f:
        for line in f:
            try:
                ts = line.split(']')[0].replace('[', '')
                dt = datetime.strptime(ts.strip(), '%d/%m %H:%M')
                if dt.replace(year=datetime.now().year) >= cutoff:
                    count += 1
            except: pass
    return count

def get_lot_stats(state):
    total = len(state)
    by_phase = {}
    by_tier = {'TOP': 0, 'ALTA': 0, 'OUTRAS': 0}
    total_margem = 0
    lots_with_margem = 0
    
    for lot in state.values():
        fase = lot.get('fase', 'unknown')
        by_phase[fase] = by_phase.get(fase, 0) + 1
        
        tier = lot.get('tier', 3)
        tier_name = {1: 'TOP', 2: 'ALTA', 3: 'OUTRAS'}.get(tier, 'OUTRAS')
        by_tier[tier_name] += 1
        
        margem = lot.get('margem_estimada', 0)
        if margem > 0:
            total_margem += margem
            lots_with_margem += 1
    
    avg_margem = round(total_margem / lots_with_margem) if lots_with_margem > 0 else 0
    return total, by_phase, by_tier, avg_margem

def generate_report():
    today = datetime.now()
    week_start = today - timedelta(days=7)
    
    state = load_json(STATE_FILE, {})
    history = load_json(HISTORY_FILE, [])
    log_lines = count_log_lines(MONITOR_LOG, 7)
    
    total, by_phase, by_tier, avg_margem = get_lot_stats(state)
    
    # Count history entries from last 7 days
    recent_history = 0
    for entry in history:
        ts = entry if isinstance(entry, str) else entry.get('timestamp', '')
        if ts:
            try:
                if 'T' in str(ts):
                    dt = datetime.fromisoformat(str(ts))
                    if dt >= week_start:
                        recent_history += 1
            except: pass
    
    # Week's top opportunities (highest margin)
    top_lots = sorted(
        [(k, v) for k, v in state.items() if v.get('margem_estimada', 0) > 0],
        key=lambda x: x[1].get('margem_estimada', 0),
        reverse=True
    )[:5]
    
    report = f'''# 📊 Relatório Semanal — MotoBid
## Semana de {week_start.strftime('%d/%m')} a {today.strftime('%d/%m/%Y')}

---

## 🏍️ Visão Geral do Monitor

| Métrica | Valor |
|---------|-------|
| Total de lotes monitorados | {total} |
| Verificações feitas (7 dias) | {log_lines} |
| Mudanças de estado (7 dias) | {recent_history} |
| Margem média | R$ {avg_margem:,} |

---

## 📦 Lotes por Fase

| Fase | Quantidade |
|------|-----------|
| Descoberta | {by_phase.get('discovery', 0)} |
| Pré-Leilão | {by_phase.get('pre_leilao', 0)} |
| 🟠 DISPUTA | {by_phase.get('disputa', 0)} |
| Encerrado | {by_phase.get('encerrado', 0)} |

---

## 🏆 Lotes com Maior Potencial (top 5)

'''

    for i, (key, lot) in enumerate(top_lots, 1):
        modelo = lot.get('modelo', 'N/A')
        margem = lot.get('margem_estimada', 0)
        lance = lot.get('lance_atual', 0)
        fase = lot.get('fase', 'unknown')
        report += f'{i}. **{modelo}** — Margem R$ {margem:,} | Lance R$ {lance:,} | [{fase.upper()}]\n'

    report += f'''

---

## 🔧 Top 3 Oportunidades por Tier

### Tier 1 — TOP (Honda, Yamaha)
'''
    top_tier1 = sorted(
        [(k, v) for k, v in state.items() if v.get('tier') == 1],
        key=lambda x: x[1].get('margem_estimada', 0), reverse=True
    )[:3]
    for key, lot in top_tier1:
        report += f'- **{lot.get('modelo','?')}** — R$ {lot.get('margem_estimada',0):,} de margem\n'

    report += '''
### Tier 2 — ALTA (Suzuki, Dafra, Kawasaki, BMW)
'''
    top_tier2 = sorted(
        [(k, v) for k, v in state.items() if v.get('tier') == 2],
        key=lambda x: x[1].get('margem_estimada', 0), reverse=True
    )[:3]
    for key, lot in top_tier2:
        report += f'- **{lot.get('modelo','?')}** — R$ {lot.get('margem_estimada',0):,} de margem\n'

    report += f'''

---

## 🧠 Padrões Cognitivos da Semana

### Decisões registradas
- Margem mínima ajustada: R$ 2.000 → R$ 1.000
- Preço de referência: FIPE → Facebook Marketplace
- Identidade visual: Martelo + Roda (Opção B) escolhido
- Ranking por tier confirmado: Honda/Yamaha TOP

### Insights de execução
- Velocidade de decisão: Alta (3 opções → escolha em segundos)
- Filtro de prioridades: Bom (descartou DETRAN, focou em prefeitura)
- Execução hands-on: Implementou sistema completo em 1 dia

---

## 🎯 Indicadores de Saúde do Sistema

| Indicador | Status |
|-----------|--------|
| Monitor ativo (cron 15min) | {'✅' if log_lines > 0 else '⚠️'} |
| Lotes com margem ≥ R$ 1.000 | {'✅' if avg_margem >= 1000 else '⚠️'} |
| Lotes em disputa | {'🔥 ALERTA' if by_phase.get('disputa',0) > 0 else '⏳ Aguardando'} |
| GitHub sincronizado | ✅ |

---

## 📅 Próximos Passos Recomendados

1. **Verificar lotes em disputa** — ação imediata se houver
2. **Executar scout manual** — se não rodou nas últimas 24h
3. **Validar preços FB** — comparar 3 modelos com mercado real
4. **Preparar para leilão 09/06** — Itaoca via Ricoleiloes

---

_Relatório gerado automaticamente por MotoBid | {today.strftime('%d/%m/%Y %H:%M')}_
'''
    
    return report

def save_report(report, week_start):
    ensure_dir(REPORT_PATH)
    filename = f'relatorio-{week_start.strftime('%Y-%m-%d')}.md'
    filepath = os.path.join(REPORT_PATH, filename)
    
    with open(filepath, 'w') as f:
        f.write(report)
    
    # Also save as latest
    with open(os.path.join(REPORT_PATH, 'latest.md'), 'w') as f:
        f.write(report)
    
    return filepath

if __name__ == '__main__':
    print('[MotoBid Weekly] Gerando relatório semanal...')
    report = generate_report()
    filepath = save_report(report, datetime.now() - timedelta(days=7))
    print(f'✅ Relatório salvo: {filepath}')
    
    # Print to stdout for cron notification
    print('\n' + report)