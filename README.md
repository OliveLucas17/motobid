# 🏍️ MotoBid — Monitor Inteligente de Leilões de Motos

**MotoBid** varre automaticamente leilões de motos em tempo real, filtra oportunidades com margem > R$ 3.000 e te notifica por email quando encontra algo bom.

## Filtros ativos
- ❌ **SEM** Honda, Yamaha, Shineray
- ✅ **COM** direito a documento (para circular)
- 💰 Margem mínima: R$ 3.000 sobre FIPE

## Plataformas monitoradas
- Sumaré Leilões (prefeituras de Vinhedo, Campinas, etc.)
- Rico Leilões (EMDEC Campinas, Prefecture Itaoca)
- Hasta SP (Prefeitura São Bernardo do Campo)

## Arquitetura
```
auto_scout.py   → Varredura automática (a cada 6h)
monitor.py      → Verificação de lotes (a cada 15min)
crawlers/       → Um módulo por plataforma
data/state.json → Lotes cadastrados + fase atual
data/alertas.json → Histórico de notificações
dashboard/      → Interface web (auto-atualizada)
```

## Dashboard (produção VM)
🔗 https://lucas170804-2e459368-5214-vm.azure.gensparkclaw.com/motobid/

## Uso local
```bash
# Scout de novos lotes
python3 auto_scout.py

# Verificar lotes existentes
python3 monitor.py
```

## Ambiente
- Python 3
- gsk CLI (crawl + search)
- Cron: scout a cada 6h, monitor a cada 15min

## Dados por fase
| Fase | Frequência | Significado |
|------|-----------|-------------|
| 🔍 Descoberta | 1x/dia | Lote novo detectado |
| 📅 Pré-Leilão | 1x/dia | Cadastrado, aguardando abertura |
| 🔥 Disputa | 15min | Guerra de lances ativa |
| ✅ Encerrado | — | Leilao fechado |

---
AlfaPrime Transportes · Lucas Oliveira · lucas170804@gmail.com