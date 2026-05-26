# CLAUDE.md — MotoBid

## Projeto
**MotoBid** — Monitor inteligente de leilões de motos para AlfaPrime Transportes.
Repo: https://github.com/OliveLucas17/motobid

## Stack
- Python 3 (lógica principal)
- gsk CLI (crawling/search)
- Cron (agendamento)
- HTML/CSS (dashboard estático)
- GitHub (versionamento)

## Arquivos importantes
- `config.py` — filtros, tiers, thresholds
- `auto_scout.py` — varredura automática (a cada 6h)
- `monitor.py` — verificação de lotes (a cada 15min)
- `crawlers/` — um módulo por plataforma
- `data/state.json` — lotes monitorados
- `dashboard/index.html` — interface web

## Sistema de Ranking (TIER)
| Tier | Marcas | Margem Mín | Score |
|------|--------|------------|-------|
| TOP | Honda, Yamaha | R$ 2.000 | 10 |
| ALTA | Suzuki, Dafra, Kawasaki, BMW | R$ 3.000 | 8 |
| OUTRAS | Kasinski, KTM, Aprilia... | R$ 4.000 | 6 |
| EXCLUÍDA | Shineray | — | reprovado |

## Critérios de filtro
- Documento OK (obrigatório)
- Margem > R$ 2.000 (TOP) / R$ 3.000 (ALTA) / R$ 4.000 (outras)
- Lance R$ 500 ~ R$ 100.000
- Score >= 5.0

## Plataformas
- Sumaré Leilões: `sumareleiloes.com.br` ✅ ativo
- Rico Leilões: `ricoleiloes.com.br` ⚠️ parcial
- Hasta SP: `hastasp.com.br` 🔜 futuro

## Agendado
- Prefeitura Itaoca: 09/06/2026 (via Rico Leilões)

## Acesso
- Dashboard: https://lucas170804-2e459368-5214-vm.azure.gensparkclaw.com/motobid/
- Servidor: porta 8082, Python HTTP

## Cres
- Não usar f-strings com aspas dentro de aspas (bug no write tool)
- Usar concatenacao de strings ou write com arquivo inteiro
- Testar syntax com `python3 -m py_compile` antes de commit

## Notas
- Sumaré bloqueia curl direto — usar `gsk crawl --render_js`
- gsk crawl timeout = 120s+
- Shineray EXCLUÍDA do monitoramento (reprovada automaticamente)
- Documento obrigatório para todos os lotes