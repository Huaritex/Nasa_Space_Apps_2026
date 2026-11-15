# RotaClima

**Idioma:** [English](../../../README.md) · [Español](../es/README.md) · Português (Brasil) · [中文（简体）](../zh-CN/README.md)

> Ferramenta de apoio à decisão agronômica para o planejamento de rotação de culturas diante das mudanças climáticas.
> Desenvolvida para o NASA Space Apps Challenge 2026, desafio **"Field Shift"**.

O RotaClima compara a rotação atual de um produtor com até três rotações alternativas. Para cada plano, executa uma simulação diária do balanço hídrico do solo e da resposta da cultura sobre **20 safras de avaliação** (2005/06–2024/25), usando dados diários da NASA POWER de **34 safras agrícolas válidas** (1991/92–2024/25). Ele reporta o rendimento relativo, o risco climático em linguagem direta ("safra ruim em 1 de cada 20 anos") e uma pontuação de saúde do solo de 0 a 100. Cada número de uma ficha de recomendação está vinculado ao conjunto de dados NASA, aos parâmetros e ao período a partir dos quais foi calculado.

**Não há aprendizado de máquina nem chatbot.** O motor é determinístico: as mesmas entradas sempre produzem as mesmas saídas.

## Conteúdo

1. Propriedades principais
2. Início rápido
3. Arquitetura
4. API
5. Fontes de dados
6. Modelo científico
7. Catálogo de culturas
8. Resultados do local de demonstração
9. Frontend
10. Validação e testes
11. Premissas e limitações
12. Estrutura do repositório
13. Problemas conhecidos
14. Documentação e traduções
15. Glossário
16. Referências

---

## 1. Propriedades principais

- **Determinístico.** Sem aleatoriedade sem semente, sem relógio no motor, desempates definidos em [PLAN.md](../../../PLAN.md) §5. O requisito de determinismo (respostas idênticas byte a byte para solicitações idênticas) está especificado como o teste P2 em PLAN §6.
- **Rastreável.** Cada afirmação traz sua evidência: conjunto de dados, nomes exatos dos parâmetros POWER, valor, unidade e período.
- **Honesto com a incerteza.** Os valores-p são reportados. Tendências com `p ≥ 0.10` são rotuladas como "não significativo". Resultados desfavoráveis são mostrados como foram calculados.
- **Nenhum preenchimento silencioso de lacunas.** O valor de preenchimento `-999` do POWER vira `NaN` em um único lugar ([backend/app/nasa/power.py](../../../backend/app/nasa/power.py)). Uma safra com entradas faltantes falha explicitamente.
- **Agronomia com fonte.** Os coeficientes vêm de FAO-56, USDA SCS-CN (TR-55), FAO EcoCrop e Teixeira et al. (2013). Cada campo agronômico de [crops.json](../../../backend/app/data/crops.json) tem uma `fuente` (fonte) e uma marca `verificar`. Os 130 campos têm atualmente `verificar: false`, ou seja, nenhum está pendente.

---

## 2. Início rápido

**Requisitos:** Python ≥ 3.11, Node.js ≥ 20 (npm ≥ 10).

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # 159 testes, sem rede; cerca de 3 minutos na máquina de desenvolvimento
uvicorn app.main:app --reload --port 8000
```

Endpoints: `GET /health`, `GET /crops`, `POST /analyze`. Documentação interativa OpenAPI: `GET /docs`.

```bash
# Frontend (segundo terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # verificação de tipos (tsc) + build de produção
```

O servidor de desenvolvimento do Vite encaminha `/analyze` e `/crops` para `http://localhost:8000`. Se o backend não responder, a interface usa a demonstração pré-armazenada de Santa Cruz e a identifica como dados de demonstração.

Scripts de dados (execute a partir de `backend/`):

```bash
python scripts/precache_demo.py         # gera frontend/public/demo_santa_cruz.json (4 perfis + backtest MODIS)
python scripts/fetch_fixture.py         # baixa o fixture do NASA POWER para testes (requer internet)
python scripts/fetch_modis_fixture.py   # baixa MOD13Q1 para 20 safras (requer internet; leva vários minutos)
```

---

## 3. Arquitetura

```
Navegador: React 19 + TypeScript (Vite)
  MapForm · ClimateShift · Compare (+ RotationEditor, CalendarChart, ModisBacktestCard, …)
        │  POST /analyze   (fallback: frontend/public/demo_santa_cruz.json)
        ▼
FastAPI  backend/app/main.py      CORS: allow_origins=["*"]; cache em processo indexado pelo SHA-256 da solicitação
        │
pipeline.py  analyze(request)     orquestração
   ├── nasa/power.py     cliente POWER: arredondamento de coordenadas, cache em disco, retentativas, -999 → NaN
   ├── nasa/modis.py     backtest MOD13Q1, somente offline (offline_only=True)
   └── engine/           funções puras: sem rede, sem E/S, sem estado global
         calendar · et0 · crop · slot · table · rotation · soil · climate · alternatives · cards
config.py               todas as constantes numéricas do motor (fonte única de verdade)
```

| Módulo | Responsabilidade |
|---|---|
| `app/main.py` | Aplicação FastAPI, CORS, manipuladores de erro (422, 503), `/health`, `/crops`, `/analyze` |
| `app/pipeline.py` | Constrói as safras, avalia as rotações, perfil climático, backtest MODIS, fichas |
| `app/schemas.py` | Contratos Pydantic v2 (solicitação e resposta) |
| `app/config.py` | Todas as constantes do motor, com referências às seções do PLAN |
| `app/data/crops.json`, `crops.py` | Catálogo de culturas e carregador com validação |
| `app/nasa/power.py` | Análise, renomeação, cache e retentativas do POWER |
| `app/nasa/modis.py` | Análise de subconjuntos MODIS, escalonamento do NDVI, backtest de Spearman |
| `engine/calendar.py` | Safras agrícolas, grade de semeadura, elegibilidade de safras |
| `engine/et0.py` | Radiação extraterrestre, Penman–Monteith, alternativa Hargreaves |
| `engine/crop.py` | Curva de Kc em quatro estágios, janela sensível de floração |
| `engine/slot.py` | Escoamento SCS-CN, balanço hídrico diário, fatores térmicos e de geada, rendimento |
| `engine/table.py` | Tabela de slots memoizada; suavização circular usada só para escolher datas de semeadura |
| `engine/rotation.py` | Validade da rotação, modos de cultivo, índices P e I, safras ruins, métricas |
| `engine/soil.py` | Pontuação de saúde do solo (nitrogênio, diversidade, proteção contra erosão, matéria orgânica) |
| `engine/climate.py` | Perfil climático, comparação antes/recente, Mann–Whitney U |
| `engine/alternatives.py` | Enumeração de planos e seleção de perfis com flexibilizações documentadas |
| `engine/cards.py` | Fichas de recomendação geradas por modelos (templates) |

Convenções do motor ([AGENTS.md](../../../AGENTS.md)): vetorizado com numpy sobre as safras, laços explícitos sobre os dias, sem literais mágicos em `engine/`.

---

## 4. API

### `POST /analyze`

Solicitação (`AnalyzeRequest`), com o caso de demonstração:

```json
{
  "lat": -17.30,
  "lon": -62.25,
  "soil_texture": "franco",
  "current_rotation": {
    "years": [
      { "slots": [
          { "crop_id": "soya", "sow_date": "11-16" },
          { "crop_id": "soya", "sow_date": "05-01" }
      ] }
    ]
  },
  "include_diversified": false
}
```

| Campo | Regra |
|---|---|
| `lat` / `lon` | `-60 … 60` / `-180 … 180`. As coordenadas são arredondadas para 2 casas decimais para acessar os dados. |
| `soil_texture` | `arenoso` \| `franco` (padrão) \| `arcilloso` |
| `sow_date` | `"MM-DD"`, o dia deve ser `01` ou `16` (quinzenas) |
| `years` | De 1 a 3 anos; de 1 a 2 slots por ano, em ordem cronológica dentro da safra |
| `crop_id` | Deve existir no catálogo (minúsculas, sem acentos: `soya`, `maiz`, …) |
| `include_diversified` | **Padrão da API: `false`.** A interface web envia `true`. |

Erros:
- **422** com `detail` (mensagem em espanhol): cultura inexistente, slots sobrepostos, menos de 10 dias entre a colheita e a próxima semeadura, rotação sem cultura colhível.
- **503** com `detail`: POWER inacessível e sem dados em cache para a coordenada.

Resposta (`AnalyzeResponse`):

| Chave | Conteúdo |
|---|---|
| `meta` | Localização, elevação, hemisfério, início da safra (`07-01` S / `01-01` N), lista de safras, períodos, fração de dias Hargreaves, nota de resolução, premissas S1–S12 |
| `climate` | 14 métricas climáticas: antes, recente, delta, valor-p, significância, série por safra, fonte |
| `climatology` | 24 quinzenas desde o início da safra, para `before` e `recent` (chuva, ET0, Tmax, Tmin) |
| `rotations` | Ordem fixa: `actual`, `adaptada`, `regenerativa` e, se solicitado, `diversificada`. Cada uma tem slots, métricas, resultados por safra e uma ficha. |
| `modis_backtest` | Objeto, ou `null` quando não há cache MODIS local para a coordenada |

`GET /crops` retorna o resumo do catálogo (ID, nome, família, indicador de colhível, quantidade de verificações pendentes).

Cache: as séries do POWER são guardadas em disco por ponto; as respostas completas de `/analyze` são guardadas em memória por processo, indexadas pelo SHA-256 do corpo da solicitação.

---

## 5. Fontes de dados

### 5.1 NASA POWER (diário, API de ponto)

- Endpoint: `https://power.larc.nasa.gov/api/temporal/daily/point`, comunidade `AG` (agroclimatologia). Não exige credenciais.
- Janela: `19910101`–`20251231` (`DATA_START`, `DATA_END`). O fixture de demonstração contém **12.784 dias consecutivos** (de 1º de janeiro de 1991 a 31 de dezembro de 2025).
- Cache em disco: `backend/cache/power/{lat:.2f}_{lon:.2f}_{start}_{end}.json` (resposta bruta).
- Cliente: timeout de 60 s; 3 tentativas no total (uma solicitação mais duas retentativas), com esperas de 2 s e depois 4 s entre elas; a falha final lança `PowerUnavailable`. A tupla de retentativas padrão do código também contém 8 s, mas com 3 tentativas ela nunca é alcançada (ver §13).
- Elevação: `geometry.coordinates[2]`.

| Parâmetro POWER | Coluna interna | Unidade | Papel no modelo |
|---|---|---|---|
| `PRECTOTCORR` | `prec` | mm/dia | Chuva; escoamento SCS-CN, balanço hídrico, perfil climático |
| `T2M_MAX` | `tmax` | °C | ET0, estresse por calor, contagem de dias quentes |
| `T2M_MIN` | `tmin` | °C | ET0, estresse por geada, GDD |
| `T2M` | `t2m` | °C | Ingerido; a ET0 usa `(tmax + tmin)/2` por desenho (FAO-56 eq. 6) |
| `RH2M` | `rh` | % | Pressão de vapor em Penman–Monteith |
| `ALLSKY_SFC_SW_DWN` | `rs` | MJ/m²/dia | Radiação líquida (CERES SYN1deg) |
| `WS2M` | `ws` | m/s | Termo de vento em Penman–Monteith |
| `PS` | `ps` | kPa | Constante psicrométrica |
| `GWETTOP` | `gwettop` | 0–1 | Ingerido; umidade superficial do solo (0–5 cm) |
| `GWETROOT` | `gwetroot` | 0–1 | Referência para a verificação de sanidade da umidade do solo (§10) |

Os nomes dos parâmetros POWER aparecem apenas em `nasa/power.py` e em `Source.parameters` da saída.

### 5.2 NASA MODIS MOD13Q1 v061 (somente validação)

- Produto: MOD13Q1 v061, 250 m, compostos de 16 dias, banda `250m_16_days_NDVI`, fator de escala 0,0001, acessado pela API de subconjuntos do ORNL DAAC.
- Usado apenas em um **backtest offline** para o ponto de demonstração. O caminho `/analyze` nunca consulta o MODIS na rede (`offline_only=True`).
- Amostragem: quatro compostos por safra na janela de verão (`A{y+1}017` … `A{y+1}065`), 20 safras → 80 compostos.
- Limites do serviço: no máximo 10 datas por solicitação (com mais, retorna HTTP 400). O projeto mediu de 33 a 42 s por solicitação.
- Cache: `backend/cache/modis/{lat:.2f}_{lon:.2f}_MOD13Q1.json`. Fixture de teste: `backend/tests/fixtures/modis_demo.json`.

---

## 6. Modelo científico

A especificação normativa completa está em [PLAN.md](../../../PLAN.md) §4. Esta seção a resume. As fórmulas são reproduzidas nos blocos de código; as constantes estão em `config.py`.

### 6.1 Safra agrícola (unidade de análise)

- Hemisfério `S` se `lat < 0`, senão `N`. A safra `y` começa em **1º de julho** (S) ou em **1º de janeiro** (N). Nunca se agrupa por ano-calendário.
- Safras válidas: `inicio(y) − 180 d ≥ DATA_START` e `inicio(y) + 365 + 183 d ≤ DATA_END` → **S: 1991–2024 (34 safras)**, **N: 1992–2024 (33)**.
- `before` = primeiras 15 safras (1991/92–2005/06). `recent` = últimas 15 (2010/11–2024/25). `eval` = últimas 20 (2005/06–2024/25). Por construção, `before` e `eval` compartilham a safra 2005/06.
- No hemisfério S, uma data de semeadura com mês ≥ 07 cai no ano-calendário `y` da safra `y`; com mês < 07, cai em `y+1`. Assim, uma cultura que cruza 31 de dezembro fica inteira.

### 6.2 Evapotranspiração de referência (ET0)

Penman–Monteith (FAO-56 eq. 6) com `T = (tmax + tmin)/2`. Hargreaves (FAO-56 eq. 52) é usado **por dia** quando faltam UR, radiação ou vento; a fração de dias com Hargreaves é reportada em `meta.et0_hargreaves_share` (0,0 na demonstração).

```
Ra     = (24·60/π)·0.0820·dr·(ωs·sin φ·sin δ + cos φ·cos δ·sin ωs)   MJ m⁻² d⁻¹   (φ em radianos, negativa no sul)
ET0_PM = (0.408·Δ·Rn + γ·900/(T+273)·ws·(es − ea)) / (Δ + γ·(1 + 0.34·ws))
ET0_HG = 0.0023·(T + 17.8)·√(tmax − tmin)·Ra·0.408                         (alternativa; Ra convertido por 0.408)
```

### 6.3 Coeficiente de cultura e janela de floração

- Kc é linear por partes em quatro estágios (inicial, desenvolvimento, médio, maturação), conforme FAO-56 tabelas 11–12. Sem ajuste climático do Kc (premissa S3).
- Janela sensível (floração): `[t_mid − 5, t_mid + 25)` dias, onde `t_mid = L_ini + L_dev`.

### 6.4 Balanço hídrico diário de um balde

- **Escoamento (SCS-CN):** `S = 25400/CN − 254`; `RO = (P − 0.2S)² / (P + 0.8S)` se `P > 0.2S`, senão 0.
- **Chuva efetiva:** chuva abaixo de `0.2 × ET0` é ignorada (`Pe = 0`). A chuva entra no balde **antes** de o fator de estresse do dia ser avaliado.
- **Balde:** capacidade `TAW = AWC × Zr`; `AWC` é 80 / 155 / 160 mm/m e `CN` é 67 / 78 / 85 para arenoso / franco / arcilloso.
- **Estresse:** `RAW = p·TAW`, com `p = clip(p_tab + 0.04·(5 − ETc), 0.1, 0.8)`; `Ks = 1` se `D ≤ RAW`, senão `(TAW − D)/(TAW − RAW)`.
- **Spin-up:** 180 dias antes da semeadura, partindo de `Dr = 0.5·TAW`. Nos últimos 120 dias, `Kc = 0.90` se o slot anterior foi colhido dentro de 30 dias (`mode = "crop"`); senão `Kc = 0.20` (`mode = "fallow"`).
- **Fator hídrico:** `f_agua = clip(1 − Ky·(1 − ΣETa/ΣETc), 0, 1)`. A razão é calculada sobre somas, nunca como média de razões diárias (FAO-56 eq. 90).

### 6.5 Fatores térmicos, geada e rendimento relativo

```
Y_rel = f_agua · f_calor · f_helada · f_temp         ∈ [0, 1]
```

- **f_temp:** média, ao longo do ciclo, de uma resposta trapezoidal do EcoCrop à temperatura média diária.
- **f_calor:** `1 − média_{janela sensível}( clip((tmax − Tcrit)/(Tlim − Tcrit), 0, 1) )`.
- **f_helada:** `0.3` se `tmin < t_helada` (0 °C) em algum dia da janela de floração; senão `0.7` se `tmin < −3 °C` em algum dia do ciclo; senão `1`. Premissa S6.
- **Fator limitante:** o fator mais baixo, se estiver abaixo de 0,95; senão `ninguno`. Empates são resolvidos na ordem agua, calor, helada, temperatura.

### 6.6 Índices de rotação e safras ruins

- Os slots formam uma sequência cíclica de 1 a 3 anos. Validade: cada intervalo entre uma colheita e a semeadura seguinte é ≥ 10 dias; `sow_offset + duração ≤ 365 + 183`; ao menos uma cultura colhível.
- Para cada safra `y`, o clima de `y` é aplicado a **cada fase** `k = 1..L` da rotação:

```
P_y = (1/L) · Σ_k Σ_{s ∈ ano k, colhível} w_s · Y_rel(s, y)
Pot = (1/L) · Σ_k Σ_{s ∈ ano k, colhível} w_s
I_y = P_y / Pot                  safra ruim ⇔ I_y < 0.60
```

- As culturas de cobertura (`cosechable = false`) não entram em `P` nem em `Pot`. Entram no solo, no modo de cultivo e na validade.
- Métricas sobre as 20 safras de avaliação: `mean_index`, `p10_index` (percentil linear), `mean_productivity`, `bad_seasons` (de 20), `bad_before` e `bad_recent` (de 15 cada), e `productivity_vs_current = 100 · mean_P / mean_P(actual)`.
- Um slot "falha" numa safra quando `Y_rel < 0.50`.

### 6.7 Pontuação de saúde do solo (0–100)

```
total = 0.25 · (nitrogen + diversity + erosion + organic_matter)
```

- **Nitrogênio:** `clip(60 + 20 · N_ano, 0, 100)`, com `N_ano = (1/L) · Σ_s N_POINTS[classe_n(s)]`. Pontos: `cobertura_leguminosa` +2.0, `leguminosa_grano` +0.5, `cobertura_no_leguminosa` +0.5, `extractiva` −1.0, `muy_extractiva` −1.5.
- **Diversidade:** `DIVERSITY_BASE[famílias] · (1 − 0.5 · fração_repetida)`, com base 30 / 65 / 85 para 1 / 2 / 3 famílias botânicas, e 100 para quatro ou mais. `fração_repetida` é a proporção de pares cíclicos adjacentes da mesma família.
- **Matéria orgânica:** `clip(100 · ((1/L) · Σ_s pts(s)) / 6, 0, 100)`, com `pts = RESIDUE_POINTS[classe]` (bajo 1, medio 2, alto 3), mais `COVER_CROP_BONUS = 1` para culturas de cobertura não colhíveis.
- **Proteção contra erosão:** o escoamento diário SCS-CN (safras de avaliação, média por dia da safra) ponderado por uma curva de cobertura, expresso em porcentagem. A cobertura é o resíduo após a colheita (`RESIDUE_COVER`: bajo 0,3, medio 0,5, alto 0,8), que cresce linearmente durante o desenvolvimento da cultura e vale 1,0 depois. Assume plantio direto (S5). Se o escoamento total for 0, a pontuação é 100.
- A pontuação de solo **não** realimenta o rendimento (premissa S4).

### 6.8 Perfil climático e teste de significância

São calculadas catorze métricas por safra (definições em [PLAN.md](../../../PLAN.md) §4.8):

- **Chuva:** total e por trimestre da safra (dias 0–90, 91–181, 182–272, 273–fim).
- **Início das chuvas (onset):** primeiro deslocamento ≥ 62 em que a chuva de 3 dias é ≥ 20 mm e não há sequência de ≥ 10 dias secos (< 1 mm/dia) nos 30 dias seguintes.
- **Fim das chuvas (cessation):** primeiro deslocamento ≥ início + 60 em que a chuva de 20 dias é < 10 mm.
- **Duração da estação chuvosa**, **dias quentes** (Tmax > 35 °C), **períodos secos** e **período seco mais longo** dentro da estação chuvosa, **GDD** (base 10 °C), **ET0 total**, **déficit hídrico**.

Para cada métrica: médias de `before` e `recent` (ignorando NaN), `delta = recent − before`, valor-p de **Mann–Whitney U** bilateral (`None` se alguma amostra tiver menos de 5 valores) e `significant = p < 0.10`.

### 6.9 Perfis alternativos

A seleção é determinística e segue [PLAN.md](../../../PLAN.md) §5. As flexibilizações são registradas em `relaxed_constraints`.

| Perfil | Objetivo | Restrições (antes de flexibilizar) | Ordenação |
|---|---|---|---|
| `actual` | Linha de base: a rotação como foi informada, sem reotimização | — | — |
| `adaptada` (adaptada ao clima) | Mudança mínima | Mesmo número de anos e slots, no máximo uma cultura trocada, datas de semeadura reotimizadas, `mean_P ≥ 95%` da atual | Menos safras ruins → maior `p10_index` → maior `mean_P` → menos trocas |
| `regenerativa` | Melhor solo com perda de produtividade limitada | Ganho de solo ≥ 10 pontos, `mean_P ≥ 80%` da atual, safras ruins não acima da atual | Maior total de solo → maior `mean_P` |
| `diversificada` (opcional) | Ciclo diversificado de dois anos | ≥ 3 famílias botânicas, ≥ 3 culturas colhíveis, solo não abaixo do atual | Maior `mean_P` entre os planos com safras ruins não acima da atual |

Ordem de flexibilização: perda de 20% → 30% em `regenerativa`; retira-se o limite de safras ruins; ganho de solo 10 → 1 ponto. `adaptada` retira seu filtro de produtividade se nenhum candidato o cumprir.

### 6.10 Fichas de recomendação

As fichas são geradas a partir de modelos fixos, não de texto livre. Cada modelo só é emitido se sua condição for atendida e cita os parâmetros de onde vêm seus números. Um teste verifica que cada número no texto de uma afirmação aparece em seu `evidence[].value` (PLAN §2.5). As fichas têm três seções: **por que**, **benefícios** e **riscos**.

---

## 7. Catálogo de culturas

O catálogo ([backend/app/data/crops.json](../../../backend/app/data/crops.json)) tem 13 culturas. Os valores abaixo foram lidos do arquivo.

| ID | Nome | Família | Colhível | Estágios ini/dev/mid/late (d) | Kc ini/mid/end | Zr (m) | p | Ky | EcoCrop Tmin/Topt-min/Topt-max/Tmax (°C) | Calor Tcrit/Tlim (°C) | Classe N | Resíduo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `soya` | Soja | Fabaceae | sim | 20/30/60/25 | 0.40/1.15/0.50 | 1.0 | 0.50 | 0.85 | 10/20/33/38 | 35/40 | leguminosa_grano | bajo |
| `maiz` | Milho | Poaceae | sim | 25/40/45/30 | 0.30/1.20/0.35 | 1.3 | 0.55 | 1.25 | 10/18/33/47 | 35/45 | muy_extractiva | alto |
| `sorgo` | Sorgo | Poaceae | sim | 20/35/40/30 | 0.30/1.05/0.55 | 1.5 | 0.55 | 0.90 | 8/22/35/40 | 35/40 | extractiva | alto |
| `trigo` | Trigo | Poaceae | sim | 15/25/50/30 | 0.30/1.15/0.30 | 1.2 | 0.55 | 1.15 | 5/15/23/27 | 27/40 | extractiva | medio |
| `girasol` | Girassol | Asteraceae | sim | 25/35/45/25 | 0.35/1.10/0.35 | 1.2 | 0.45 | 0.95 | 5/17/34/45 | 34/45 | muy_extractiva | medio |
| `frijol` | Feijão | Fabaceae | sim | 20/30/40/20 | 0.40/1.15/0.35 | 0.7 | 0.45 | 1.15 | 7/16/25/32 | 25/32 | leguminosa_grano | bajo |
| `mani` | Amendoim | Fabaceae | sim | 25/35/45/25 | 0.40/1.15/0.60 | 0.8 | 0.50 | 0.70 | 10/22/32/45 | 32/45 | leguminosa_grano | bajo |
| `algodon` | Algodão | Malvaceae | sim | 30/50/55/45 | 0.35/1.15/0.60 | 1.4 | 0.65 | 0.85 | 15/22/36/42 | 36/42 | muy_extractiva | bajo |
| `cebada` | Cevada | Poaceae | sim | 15/25/50/30 | 0.30/1.15/0.25 | 1.2 | 0.55 | 1.15 | 2/15/20/40 | 20/40 | extractiva | medio |
| `papa` | Batata | Solanaceae | sim | 25/30/45/30 | 0.50/1.15/0.75 | 0.5 | 0.35 | 1.10 | 7/15/25/30 | 25/30 | extractiva | bajo |
| `mijo` | Painço | Poaceae | sim | 15/25/40/25 | 0.30/1.00/0.30 | 1.5 | 0.55 | 0.90 | 12/25/35/40 | 35/40 | extractiva | alto |
| `avena_cob` | Aveia (cobertura) | Poaceae | **não** | 15/25/45/5 | 0.30/1.15/1.15 | 1.2 | 0.55 | 1.00 | 5/16/20/30 | 20/30 | cobertura_no_leguminosa | alto |
| `crotalaria` | Crotalária (cobertura) | Fabaceae | **não** | 15/25/45/5 | 0.40/1.10/1.10 | 1.0 | 0.50 | 1.00 | 15/23/30/37 | 30/37 | cobertura_leguminosa | alto |

As culturas de cobertura são truncadas em um ciclo de 90 dias com Kc_end = Kc_mid (premissa S9). Os limiares de calor das culturas fora de Teixeira et al. (2013) são derivados do EcoCrop (S7). O limiar de geada `t_helada` é 0 °C para todas (S6).

---

## 8. Resultados do local de demonstração

Ponto de demonstração: **Santa Cruz, Bolívia (−17.30, −62.25), elevação 280.15 m**, textura `franco` (AWC 155 mm/m, CN 78). Rotação atual: soja 11-16 + soja 05-01. Todos os valores abaixo foram lidos de [frontend/public/demo_santa_cruz.json](../../../frontend/public/demo_santa_cruz.json).

### 8.1 Mudança climática (antes 1991/92–2005/06 vs recente 2010/11–2024/25)

| Métrica | Unidade | Antes | Recente | Delta | Valor-p | Significativo (p < 0.10) |
|---|---|---|---|---|---|---|
| Chuva total | mm/safra | 1342.0 | 1146.0 | −195.9 | 0.0114 | sim |
| Chuva, trimestre 1 | mm | 145.4 | 142.7 | −2.73 | 0.9669 | não |
| Chuva, trimestre 2 | mm | 466.2 | 287.9 | −178.3 | 0.0006 | sim |
| Chuva, trimestre 3 | mm | 493.3 | 436.6 | −56.64 | 0.2290 | não |
| Chuva, trimestre 4 | mm | 237.3 | 279.1 | +41.79 | 0.2455 | não |
| Início das chuvas | deslocamento em dias | 82.6 | 110.2 | +27.6 | 0.0016 | sim |
| Fim das chuvas | deslocamento em dias | 312.9 | 274.8 | −38.12 | 0.0723 | sim |
| Duração da estação chuvosa | dias | 232.1 | 168.0 | −64.1 | 0.0055 | sim |
| Dias quentes (Tmax > 35 °C) | dias/safra | 52.73 | 80.47 | +27.73 | 0.0084 | sim |
| Períodos secos (≥ 10 d) | contagem | 1.00 | 1.73 | +0.73 | 0.0791 | sim |
| Período seco mais longo | dias | 11.00 | 13.47 | +2.47 | 0.0828 | sim |
| GDD (base 10 °C) | °C·dia | 5694 | 5934 | +240.4 | 0.0202 | sim |
| ET0 total | mm/safra | 1522 | 1587 | +65.02 | 0.1057 | **não** |
| Déficit hídrico | mm/safra | 470.7 | 659.0 | +188.3 | 0.0101 | sim |

Dez das 14 métricas são significativas. As quatro que não são (chuva dos trimestres 1, 3 e 4, e ET0 total) são reportadas como tal.

### 8.2 Perfis de rotação (janela de avaliação, 20 safras)

| Perfil | Rotação (ano 1 · ano 2) | I médio | I P10 | Produtividade vs atual | Safras ruins | Solo total | N | Diversidade | Proteção contra erosão | Matéria orgânica |
|---|---|---|---|---|---|---|---|---|---|---|
| `actual` | soya@11-16 + soya@05-01 | 0.7644 | 0.6812 | 100.00 % | 1 / 20 | 47.90 | 80.0 | 15.0 | 63.26 % | 33.33 |
| `adaptada` | mijo@11-16 + soya@03-16 | 0.8589 | 0.7779 | 112.36 % | 0 / 20 | 63.82 | 50.0 | 65.0 | 73.60 % | 66.67 |
| `regenerativa` | crotalaria@10-16 + sorgo@02-16 · girasol@11-01 + mijo@04-16 | 0.8795 | 0.8277 | 86.30 % | 0 / 20 | 79.03 | 45.0 | 85.0 | 86.12 % | 100.00 |
| `diversificada` | algodon@09-16 + sorgo@04-01 · mijo@11-16 + girasol@03-16 | 0.8819 | 0.7958 | 115.37 % | 0 / 20 | 60.56 | 10.0 | 74.38 | 82.88 % | 75.00 |

As piores safras da rotação atual: **2016/17** (I = 0.5541, fator limitante: calor), **2023/24** (I = 0.6796, água) e **2015/16** (I = 0.6814, água).

`adaptada` troca uma cultura (soja → painço) e reotimiza as datas de semeadura dentro da mesma estrutura de um ano. `regenerativa` e `diversificada` são ciclos de dois anos. `regenerativa` tem a maior pontuação de solo; `diversificada` tem a maior produtividade, mas a menor pontuação de nitrogênio (10.0), porque não inclui leguminosas.

### 8.3 Validação por satélite (MODIS MOD13Q1, offline)

- Correlação de postos de Spearman entre o máximo de NDVI do verão e o índice simulado `I` da rotação atual: **ρ = −0.0617, p = 0.7962** (n = 20). Não há correlação significativa. Reportado como calculado.
- Limiar do tercil inferior de NDVI: **0.7260**. A única safra ruim, 2016/17, tem NDVI máximo de **0.7160**, portanto cai no tercil inferior (**1 de 1** safras ruins).

Interpretação: um pixel de 250 m reflete as culturas efetivamente plantadas naquele talhão a cada ano, enquanto o modelo simula uma rotação fixa dirigida por um clima regional de cerca de 50 km. Não se espera uma correlação estreita entre os dois em anos normais.

---

## 9. Frontend

Stack: Vite, React 19, TypeScript em modo estrito, Leaflet (`react-leaflet`), Recharts. **Os rótulos da interface estão em espanhol.** Identificadores e código estão em inglês.

| Área | Componentes | O que faz |
|---|---|---|
| Talhão e rotação (a) | `views/MapForm.tsx`, `components/RotationEditor.tsx` | Mapa Leaflet com captura de coordenadas por clique, seletor de textura, editor de rotação por quinzenas com validação de sobreposição e de intervalos, botão de demonstração de Santa Cruz |
| Mudança climática (b) | `views/ClimateShift.tsx`, `components/MetricDelta.tsx` | Um cartão por métrica climática (antes → recente, delta, "No significativo" quando p ≥ 0.10), série por safra, fonte NASA |
| Calendário | `components/CalendarChart.tsx` | Gráfico de chuva e ET0 em 24 quinzenas, linhas de Tmax/Tmin, barras de estágios da cultura com a janela de floração destacada |
| Comparação (c) | `views/Compare.tsx`, `components/CompareTable.tsx`, `components/RotationCard.tsx`, `components/ModisBacktestCard.tsx` | Perfis lado a lado, faixa de safras ruins das 20 safras, fichas com por quê/benefícios/riscos, chips de evidência por afirmação, cartão MODIS |
| Cliente de API | `src/api.ts`, `src/types.ts` | Chama `/analyze` e `/crops`; recorre à demonstração pré-armazenada e à lista estática de culturas; `types.ts` espelha `schemas.py` manualmente |

A barra superior mostra um aviso de **demonstração offline** quando os dados vêm do arquivo pré-armazenado.

---

## 10. Validação e testes

- **Suíte do backend:** `pytest -q` → **159 passed, 1 warning**, cerca de 3 minutos na máquina de desenvolvimento. Os testes rodam sem rede: usam fixtures em `backend/tests/fixtures/` ou `httpx.MockTransport`.
- **Frontend:** `npm run build` executa `tsc` em modo estrito e depois o build do Vite.
- **Critérios go/no-go** ([PLAN.md](../../../PLAN.md) §3, N1–N2), no [notebooks/01_validacion_motor.ipynb](../../../notebooks/01_validacion_motor.ipynb):
  1. ET0 anual entre 1.100 e 2.000 mm, e chuva anual entre 700 e 1.800 mm.
  2. A soja de verão rende mais que a soja de inverno.
  3. A rotação atual tem entre 1 e 15 safras ruins de 20.
  4. As três piores safras são comparadas com secas relatadas.
  5. Correlação entre `1 − Dr/TAW` simulado e `gwetroot` acima de 0,5. É uma **verificação de sanidade, não uma validação independente**, porque ambos usam a mesma chuva.

  O notebook **não foi reexecutado** para esta documentação. Os resultados reportados nos documentos anteriores do projeto, incluindo r = 0,5501 para o critério 5, não foram recalculados aqui.

---

## 11. Premissas e limitações

Estas são as premissas S1–S12 de [PLAN.md](../../../PLAN.md) §4.10. Elas também são retornadas em `meta.assumptions`.

- **S1** O POWER é reanálise a ≈ 50 km (MERRA-2), com radiação de 1° (CERES). Descreve o clima regional, não um talhão específico. A Tmax modelada tende a ficar abaixo das estações, então as contagens de dias acima de 35 °C são conservadoras.
- **S2** Água inicial: spin-up de 180 dias com Kc fixo de 0,20 (pousio) ou 0,90 (cultura anterior). A cultura anterior real não é simulada.
- **S3** A fenologia usa dias de calendário. Kc não é ajustado por umidade nem vento. Sem fotoperíodo.
- **S4** A pontuação de solo não altera o rendimento simulado.
- **S5** Assume-se manejo em plantio direto.
- **S6** A geada é uma regra em degrau: fator 0,3 durante a floração, 0,7 na fase vegetativa.
- **S7** Limiares de calor que não estão em Teixeira et al. (2013) são derivados do EcoCrop.
- **S8** As classes de nitrogênio e de resíduo são conhecimento agronômico geral, não medição.
- **S9** Culturas de cobertura usam parâmetros por analogia, um ciclo truncado de 90 dias e não produzem grão.
- **S10** O rendimento é relativo ao potencial agroecológico. Não há preços nem margens. `value_weight = 1` para todas as culturas por padrão.
- **S11** Modelo de balde único. Não são modelados: alagamento, pragas, plantas daninhas, falhas de emergência, águas subterrâneas, ascensão capilar, dinâmica de nutrientes e mudanças da estrutura do solo ao longo do tempo.
- **S12** Tendências de chuva em reanálises podem conter artefatos do sistema de observação. Daí os valores-p e o rótulo "não significativo" quando `p ≥ 0.10`.

Limites de escopo decorrentes dessas premissas:
- O motor avalia um ponto por solicitação. Uma comparação regional exige uma solicitação por coordenada.
- A saída é um ranking relativo sob um modelo de rotação fixo. Não é uma previsão de rendimento nem uma previsão sazonal.
- A pontuação de solo e o rendimento são independentes: uma pontuação de solo maior não eleva o rendimento simulado.

---

## 12. Estrutura do repositório

```
.
├── README.md                     # este arquivo (versão mestra em inglês)
├── AGENTS.md                     # regras de engenharia para colaboradores e agentes
├── PLAN.md                       # plano normativo: contratos (§2), fórmulas (§4), testes (§6)
├── docs/i18n/
│   ├── es/README.md              # Español
│   ├── pt-BR/README.md           # Português (Brasil)
│   └── zh-CN/README.md           # 中文（简体）
├── backend/
│   ├── pyproject.toml            # dependências e o extra de desenvolvimento (pytest)
│   ├── app/
│   │   ├── main.py               # endpoints FastAPI, CORS, manipuladores de erro
│   │   ├── pipeline.py           # analyze(): orquestração e cache em memória
│   │   ├── schemas.py            # contratos Pydantic v2
│   │   ├── config.py             # todas as constantes do motor
│   │   ├── data/                 # crops.json e seu carregador
│   │   ├── nasa/                 # power.py (cliente POWER), modis.py (backtest MODIS)
│   │   └── engine/               # funções puras: calendar, et0, crop, slot, table,
│   │                             #   rotation, soil, climate, alternatives, cards
│   ├── scripts/                  # scripts de dados canônicos (ver §13)
│   └── tests/                    # test_*.py e fixtures/
├── frontend/
│   ├── package.json · vite.config.ts · tsconfig.json · index.html
│   ├── public/demo_santa_cruz.json   # demonstração offline pré-armazenada
│   └── src/                      # App.tsx, api.ts, types.ts, views/, components/
├── notebooks/01_validacion_motor.ipynb
└── contracts/analyze_response.example.json
```

Gerado e ignorado pelo git: `backend/cache/`, `backend/.venv/`, `frontend/node_modules/`, `frontend/dist/`.

---

## 13. Problemas conhecidos

- **Wrappers em `scripts/` na raiz.** `scripts/` na raiz contém dois wrappers (`fetch_fixture.py`, `precache_demo.py`) que delegam aos arquivos de mesmo nome em `backend/scripts/`. Os comandos deste documento são executados a partir de `backend/`; os wrappers são um ponto de entrada alternativo. `fetch_modis_fixture.py` não tem wrapper na raiz.
- **Arquivo ausente.** [AGENTS.md](../../../AGENTS.md) e [PLAN.md](../../../PLAN.md) citam `QUESTIONS.md` como o lugar das dúvidas abertas. Ele não está no repositório.
- **Sem arquivo de licença.** O repositório não declara uma licença; portanto, não há termos de reutilização definidos.
- **O padrão de diversificada difere conforme o cliente.** O padrão da API é `include_diversified: false`; a interface web envia `true`.
- **Cache frio.** Sem `backend/cache/`, o primeiro `/analyze` de uma nova coordenada precisa de rede para consultar o POWER. A demonstração pré-armazenada em `frontend/public/` funciona offline. A interface avisa que uma primeira consulta pode levar cerca de 20 segundos.
- **Cobertura do proxy de desenvolvimento.** O proxy do Vite encaminha apenas `/analyze` e `/crops`, não `/health`. Defina `VITE_API_URL` para chamar o backend a partir de outra origem.
- **Escopo do MODIS.** O backtest MODIS é pré-armazenado e offline por desenho. Não pode rodar para coordenadas sem cache MODIS local; nesse caso o campo `modis_backtest` é `null`.
- **Retentativas do POWER diferentes do plano.** [PLAN.md](../../../PLAN.md) §2.3 especifica três retentativas com esperas de 2, 4 e 8 s. [backend/app/nasa/power.py](../../../backend/app/nasa/power.py) faz 3 tentativas no total (2 retentativas) com esperas de 2 s e 4 s. O código é o comportamento de referência; o plano não foi atualizado.

---

## 14. Documentação e traduções

- A **versão em inglês deste arquivo é a mestra.** As versões em espanhol, português brasileiro e chinês simplificado em [docs/i18n/](../../) são traduções dela.
- Fórmulas, blocos de código, identificadores, IDs de culturas, nomes de parâmetros POWER e MODIS, caminhos de arquivos e nomes de campos da API são idênticos nas quatro versões.
- As traduções são mantidas manualmente. Quando este arquivo mudar, atualize as traduções no mesmo commit.

---

## 15. Glossário

| Termo | Significado |
|---|---|
| Safra (*campaña*) | Ano agrícola a partir de 1º de julho (S) ou 1º de janeiro (N). É a unidade de análise. |
| Slot | Uma cultura com sua data de semeadura e seu modo de cultivo: (cultura, data de semeadura, `crop` \| `fallow`) |
| Modo | `crop` se a colheita anterior ocorreu até 30 dias antes da semeadura; senão `fallow` |
| TAW | Água total disponível na zona radicular (mm) |
| RAW | Água prontamente disponível, `p · TAW` (mm) |
| Dr | Depleção da zona radicular (mm) |
| Y_rel | Rendimento relativo de um slot numa safra, 0–1 |
| P, Pot, I | Produtividade, potencial e índice de uma rotação numa safra |
| Safra ruim | Safra com `I < 0.60` |
| Janela de avaliação | As últimas 20 safras, usadas em todas as métricas principais |

---

## 16. Referências

- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56.
- Doorenbos, J., & Kassam, A. H. (1979). *Yield response to water.* FAO Irrigation and Drainage Paper 33 (fonte do fator de resposta de rendimento Ky).
- USDA Soil Conservation Service. *National Engineering Handbook, Section 4 (Hydrology)*, e TR-55 (método do número de curva).
- Teixeira, E. I., et al. (2013). *Global and Planetary Change* (limiares de estresse térmico).
- Base de dados FAO ECOCROP (faixas de adequação térmica).
- NASA POWER (Prediction Of Worldwide Energy Resources), Langley Research Center. Conjuntos de dados MERRA-2 e CERES SYN1deg.
- MODIS MOD13Q1 v061, 250 m, NDVI de 16 dias, acessado pela API de subconjuntos do ORNL DAAC.
