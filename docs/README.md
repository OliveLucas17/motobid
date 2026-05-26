# MotoBid — Monitor Inteligente de Leilões de Motos

## 1. Visão Geral

**MotoBid** é um sistema de monitoramento automático de leilões de motos criado para a **AlfaPrime Transportes**. O sistema varre automaticamente plataformas de leilão governamental, filtra oportunidades com base em critérios de lucratividade e notifica o time quando encontra bikes com margem > R$ 2.000.

**Objetivo:** Encontrar motos em leilão público (prefeituras) abaixo do valor de mercado, comprar com desconto e revender com margem.

**Dashboard:** https://lucas170804-2e459368-5214-vm.azure.gensparkclaw.com/motobid/

---

## 2. Modelo de Negócio

### Estratégia de Compra e Revenda

```
Leilão Governamental (Prefeitura)
    ↓ compra abaixo valor FIPE
Revenda para pessoa física ou B2B (Ambev, iFood, etc.)
    ↓ margem ≥ R$ 2.000
Lucro por moto: R$ 2.000 ~ R$ 12.000
```

### Por que leilões de prefeitura?
- Preço mais baixo que arremates comuns
- Veículos conservados com documento (IPVA pago, licenciado)
- Leiloeiro idôneo (confiança legal)
- Mesma mecânica do Sumaré (referência comprovada)

### Segmento de mercado (B2B)
- Locadoras de moto (Ambev, iFood, James)
- Empresas com frotas (logística última milha)
- Ambulâncias / delivery

---

## 3. Plataformas Monitoradas

| Plataforma | URL | Status | Tipo |
|-----------|-----|--------|------|
| **Sumaré Leilões** | sumareleiloes.com.br | ✅ Ativo | Prefeitura (Vinhedo, Sumaré, etc.) |
| **Rico Leilões** | ricoleiloes.com.br | ⚠️ Parcial | EMDEC Campinas, Prefeitura Itaoca |
| **Hasta SP** | hastasp.com.br | 🔜 Futuro | Prefeitura São Bernardo do Campo |

### Sumaré Leilões (principais leilões ativos)
- Leilão 5105 — Prefeitura Vinhedo (4 bikes monitoradas)
- Leilão 1905 — **51 lotes, bikes com Honda** ← prioridade
- Leilão 2511 — **45 lotes, bikes com Honda** ← prioridade
- Leilão 2530, 3174, 3200, 3411 — bikes diversas

### Rico Leilões (agendado)
- **Prefeitura Itaoca — 09/06/2026**
- Tipo: Veículos Conservados (Com direito a documento)
- Status: Aguardando abertura (previsto 01/06/2026)

---

## 4. Sistema de Ranking de Marcas

O sistema classifica cada lote em tiers baseados no potencial de revenda:

| Tier | Nome | Marcas | Margem Mínima | Score Base |
|------|------|--------|---------------|------------|
| ⭐ 1 | **TOP** | Honda, Yamaha | R$ 2.000 | 10/10 |
| 🔷 2 | **ALTA** | Suzuki, Dafra, Kawasaki, BMW | R$ 3.000 | 8/10 |
| 📦 3 | **OUTRAS** | Kasinski, KTM, Aprilia, Royal Enfield | R$ 4.000 | 6/10 |
| ❌ X | **Excluída** | Shineray | — | reprovado |

**Por que Honda/Yamaha no topo?**
- São as mais vendidas do Brasil
- Peças abundantes e baratas
- Manutenção fácil
- revendem rápido (liquidez)
- Para locadora B2B, são o padrão da indústria

### Fórmula do Score
```
score = (tier_score) + (documento_ok ? 2 : 0) + (margem/3000 * 3) + (ano >= 2022 ? 1.5 : 0)
```

| Componente | Peso |
|------------|------|
| Tier da marca | 6~10 pts |
| Documento OK | +2 pts |
| Margem sobre FIPE | até +5 pts |
| Ano 2022+ | +1.5 pts |
| **Máximo** | **10/10** |

---

## 5. Filtros e Critérios

### Obrigatórios para entrar no monitoring
- ✅ **Documento OK** — texto deve conter: `com direito a documento`, `para circular`, `documento ok`, `ipva ok`, `licenciado`
- ✅ **Margem >** R$ 2.000 (Honda/Yamaha) ou R$ 3.000 (outras)
- ✅ **Lance entre** R$ 500 e R$ 100.000
- ✅ **Score >=** 5.0

### Exclusivos (reprovados automaticamente)
- ❌ **Shineray** — mercado de peças restrito, revenda difícil
- ❌ **Veículos com COLISÃO** ( Copart, etc.)
- ❌ **Sem documento / sucata**

---

## 6. Arquitetura Técnica

### Stack
```
Python 3         → Lógica principal
gsk CLI          → Crawling e search
Cron (Linux)     → Agendamento
HTML/CSS/JS      → Dashboard (sem backend)
GitHub           → Versionamento e coordenação com Claude Code
Caddy (proxy)    → HTTPS + roteamento
```

### Estrutura de arquivos
```
motobid/
├── auto_scout.py        # Varredura automática (a cada 6h)
├── monitor.py           # Verificação de lotes (a cada 15min)
├── config.py            # Filtros, tiers, thresholds, sites
├── run_monitor.py       # Wrapper com retry
├── crawlers/
│   ├── sumare.py        # Sumaré Leilões
│   ├── ricoleiloes.py   # Rico Leilões (placeholder)
│   └── hastasp.py       # Hasta SP (placeholder)
├── data/
│   ├── state.json       # Lotes monitorados (estado atual)
│   ├── history.json     # Histórico de verificações
│   ├── alertas.json     # Alertas gerados
│   ├── scout.log        # Log do scout
│   └── monitor.log      # Log do monitor
├── dashboard/
│   └── index.html       # Interface web (single-page)
├── docs/                # Esta documentação
└── README.md            # README rápido
```

### Fluxo de Dados
```
auto_scout.py (6h)
    ↓ acha novos lotes
    ↓ aplica filtros (brand, documento, margem)
    ↓ adiciona em state.json
    ↓ envia email para lucas170804@gmail.com
    ↓ log em scout.log

monitor.py (15min)
    ↓ verifica preços dos lotes
    ↓ detecta mudança de fase
    ↓ gera dashboard HTML
    ↓ alertar se disputa ou variação >15%
    ↓ log em monitor.log
```

---

## 7. Fases do Lote

Cada lote monitorado passa por fases conforme o ciclo do leilão:

| Fase | Descrição | Frequência de Verificação |
|------|-----------|--------------------------|
| 🔍 **discovery** | Lote novo detectado pelo scout | 1x ao dia |
| 📅 **pre_leilao** | Cadastrado, aguardando abertura do leilão | 1x ao dia |
| 🔥 **disputa** | Guerra de lances ativa | A cada 15 min |
| ✅ **encerrado** | Leilão fechado | Removido do ciclo |

### Detecção de fase
- `discovery` → scout acabou de encontrar
- `pre_leilao` → lote tem data de leilão futura
- `disputa` → data atual está dentro do período do leilão E lance atual > lance inicial
- `encerrado` → data atual > data fim do leilão

---

## 8. Dashboard

**URL:** https://lucas170804-2e459368-5214-vm.azure.gensparkclaw.com/motobid/

O dashboard é um arquivo HTML estático gerado pelo `monitor.py` a cada execução. Não precisa de backend — é servido diretamente pelo Python HTTP server na porta 8082.

### Elementos do dashboard
- **Header** — logo MotoBid, hora atual, status
- **Banner de scout** — próxima ação programada, filtros ativos
- **Barra de fases** — contagem por fase (discovery/pre/disputa/encerrado)
- **Cards de lotes** — cada lote com:
  - ID + fase (badge colorido)
  - Modelo + ano + cor
  - Score (barra visual)
  - Métricas: lance atual, FIPE estimado, margem
  - Barras comparativas: lance vs FIPE
  - Link para página original do lote
- **Alertas** — últimos发生的事情

### Atualização
- Auto-refresh a cada 15 minutos (meta tag refresh)
- Atualização manual: apertar F5

---

## 9. Cron Jobs

```cron
# Scout - varredura de novos lotes (a cada 6h)
0 */6 * * * cd /home/work/.openclaw/workspace/projects/motobid && python3 auto_scout.py >> data/scout.log 2>&1

# Monitor - verificação de lotes existentes (a cada 15min)
*/15 * * * * cd /home/work/.openclaw/workspace/projects/motobid && python3 run_monitor.py >> data/monitor.log 2>&1
```

### Decisões de frequência inteligente
- `discovery`/`pre_leilao` → só roda 1x por dia (evita spam)
- `disputa` → a cada 15min (precisa acompanhar guerra de lances)
- `encerrado` → não verifica (leilão fechado)

---

## 10. Estimativa de Preço FIPE

O sistema usa uma tabela interna de preços estimados por marca/modelo. Não faz consulta real à Tabela FIPE (futura melhoria).

### Tabela de referência (valores aproximados 2024-2025)
| Marca | Modelo | Preço Estimado |
|-------|--------|---------------|
| Honda | CG 160 Start | R$ 16.500 |
| Honda | CG 160 Fan | R$ 15.000 |
| Honda | Biz 125 | R$ 11.000 |
| Honda | PCX 150 | R$ 16.000 |
| Yamaha | Fazer 250 | R$ 15.000 |
| Yamaha | Factor 150 | R$ 13.000 |
| Yamaha | NMAX 160 | R$ 16.500 |
| Suzuki | Yes 125 | R$ 14.000 |
| Dafra | City 150 | R$ 9.500 |
| Kawasaki | Ninja 300 | R$ 25.000 |

**Melhoria futura:** Integrar com API real da Tabela FIPE para precisão.

---

## 11. Integração GitHub

O código está versionado no GitHub para permitir desenvolvimento colaborativo:

```
https://github.com/OliveLucas17/motobid (privado)
```

### Fluxo de trabalho
1. **Desenvolvimento** → código no GitHub (Claude Code ou 직접)
2. **Execução** → VM roda cron 24/7, serve dashboard
3. **Sincronização** → push/pull via Git

### Arquivos importantes no repo
- `CLAUDE.md` — contexto do projeto para Claude Code
- `.gitignore` — ignora state.json, logs, arquivos sensíveis
- `README.md` — documentação rápida

---

## 12. Histórico de Execução

### 26/05/2026 — Setup inicial
- Sistema criado com arquitetura modular
- Implementado ranking por tier (Honda/Yamaha TOP)
- Dashboard no ar em `/motobid/`
- 4 lotes monitorados (3 Honda, 1 Shineray) do leilão 5105 Vinhedo

### Lotes atuais em monitoring
| Lote | Modelo | Tier | Score | Margem |
|------|--------|------|-------|--------|
| 0054 | Honda CG 160 Start 24/24 | TOP | 10/10 | R$ 10.522 |
| 0056 | Honda CG 160 Fan 21/21 | TOP | 10/10 | R$ 9.737 |
| 0065 | Honda CG 160 Start 23/23 | TOP | 10/10 | R$ 10.008 |
| 0059 | Shineray XY125-6A 25/25 | EXCLUÍDA | — | R$ 5.712 |

---

## 13. Limitações e Melhorias Futuras

### Atuais
- `gsk crawl` timeout na Rico Leilões (página pesada)
- Sumaré bloqueia acesso via curl — usa `gsk crawl --render_js`
- Sem consulta real à Tabela FIPE (usa estimado interno)
- Rico Leilões remove páginas após fechamento — precisa captar no dia que abre
- Crawlers de Rico e Hasta SP ainda são placeholders

### Roadmap
1. **Crawler completo da Ricoleiloes** — parse real dos lotes
2. **Crawler da Hasta SP** — integração com prefeitura São Bernardo
3. **API FIPE real** — precisão nos preços
4. **Alertas por WhatsApp** — notificação instantânea
5. **Dashboard com gráfico histórico** — sparklines de preço
6. **Filtro por cidade/prefeitura** — só prefeituras confiáveis

---

## 14. Como Contribuir / Desenvolver

```bash
# Clone o repo
git clone https://github.com/OliveLucas17/motobid
cd motobid

# Desenvolva melhorias
# (edite auto_scout.py, monitor.py, crawlers/, etc.)

# Teste local
python3 auto_scout.py
python3 monitor.py

# Commit e push
git add .
git commit -m 'descrição da mudança'
git push

# VM puxa automaticamente (cron)
```

---

**AlfaPrime Transportes · Lucas Oliveira · lucas170804@gmail.com**
**MotoBid — achando oportunidades enquanto você dorme** 🏍️