# RotaClima

**语言：** [English](../../../README.md) · [Español](../es/README.md) · [Português (Brasil)](../pt-BR/README.md) · 中文（简体）

> 面向气候变化下作物轮作规划的农艺决策支持工具。
> 为 NASA Space Apps Challenge 2026 开发，挑战题目为 **"Field Shift"**。

RotaClima 将农户当前的轮作与最多三种替代轮作进行比较。对每个方案，它使用 NASA POWER 的逐日数据，在 **20 个评估农业季**（2005/06–2024/25）上模拟逐日土壤水分平衡和作物响应，全部有效农业季共 **34 个**（1991/92–2024/25）。输出相对产量、通俗表述的气候风险（例如"每 20 年中有 1 年为歉收季"），以及 0 到 100 的土壤健康评分。推荐卡片中的每个数字都关联到计算它所用的 NASA 数据集、参数和时段。

**不使用机器学习，也不使用聊天机器人。** 引擎是确定性的：相同输入总是得到相同输出。

## 目录

1. 主要特性
2. 快速开始
3. 架构
4. API
5. 数据来源
6. 科学模型
7. 作物目录
8. 示范地点的结果
9. 前端
10. 验证与测试
11. 假设与局限
12. 仓库结构
13. 已知问题
14. 文档与翻译
15. 术语表
16. 参考文献

---

## 1. 主要特性

- **确定性。** 没有未设种子的随机数，引擎中没有时钟，平局规则在 PLAN §5 中定义。确定性要求（相同请求得到逐字节相同的响应）在 PLAN §6 中以测试 P2 的形式规定。
- **可追溯。** 每个论断都附有证据：数据集、精确的 POWER 参数名、数值、单位和时段。
- **诚实面对不确定性。** 报告 p 值。`p ≥ 0.10` 的趋势标注为"不显著"。不利结果按计算结果如实展示。
- **不静默填补缺失值。** POWER 的填充值 `-999` 只在一处转换为 `NaN`（[backend/app/nasa/power.py](../../../backend/app/nasa/power.py)）。输入缺失的农业季会明确报错。
- **农艺参数有来源。** 系数来自 FAO-56、USDA SCS-CN（TR-55）、FAO EcoCrop 和 Teixeira 等人（2013）。[crops.json](../../../backend/app/data/crops.json) 中每个农艺字段都有 `fuente`（来源）和 `verificar` 标志。全部 130 个字段当前为 `verificar: false`，即没有待核实项。

---

## 2. 快速开始

**环境要求：** Python ≥ 3.11，Node.js ≥ 20（npm ≥ 10）。

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # 159 个测试，离线运行；在开发机上约 3 分钟
uvicorn app.main:app --reload --port 8000
```

端点：`GET /health`、`GET /crops`、`POST /analyze`。交互式 OpenAPI 文档：`GET /docs`。

```bash
# 前端（第二个终端）
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # 类型检查（tsc）+ 生产构建
```

Vite 开发服务器把 `/analyze` 和 `/crops` 代理到 `http://localhost:8000`。如果后端不可用，界面会回退到预缓存的圣克鲁斯示范数据，并将其标注为示范数据。

数据脚本（在 `backend/` 目录下运行）：

```bash
python scripts/precache_demo.py         # 生成 frontend/public/demo_santa_cruz.json（4 个方案 + MODIS 回测）
python scripts/fetch_fixture.py         # 下载测试用的 NASA POWER 样本（需要网络）
python scripts/fetch_modis_fixture.py   # 下载 20 个农业季的 MOD13Q1（需要网络；耗时数分钟）
```

---

## 3. 架构

```
浏览器：React 19 + TypeScript（Vite）
  MapForm · ClimateShift · Compare（+ RotationEditor、CalendarChart、ModisBacktestCard 等）
        │  POST /analyze   （回退：frontend/public/demo_santa_cruz.json）
        ▼
FastAPI  backend/app/main.py      CORS：allow_origins=["*"]；进程内缓存，键为请求的 SHA-256
        │
pipeline.py  analyze(request)     编排
   ├── nasa/power.py     POWER 客户端：坐标取整、磁盘缓存、重试、-999 → NaN
   ├── nasa/modis.py     MOD13Q1 回测，仅离线（offline_only=True）
   └── engine/           纯函数：无网络、无 I/O、无全局状态
         calendar · et0 · crop · slot · table · rotation · soil · climate · alternatives · cards
config.py               引擎的全部数值常量（唯一信息来源）
```

| 模块 | 职责 |
|---|---|
| `app/main.py` | FastAPI 应用、CORS、错误处理（422、503）、`/health`、`/crops`、`/analyze` |
| `app/pipeline.py` | 构建农业季、评估轮作、气候方案、MODIS 回测、卡片 |
| `app/schemas.py` | Pydantic v2 契约（请求与响应） |
| `app/config.py` | 引擎的全部常量，并附 PLAN 章节引用 |
| `app/data/crops.json`、`crops.py` | 作物目录及带校验的加载器 |
| `app/nasa/power.py` | POWER 解析、重命名、缓存、重试 |
| `app/nasa/modis.py` | MODIS 子集解析、NDVI 换算、Spearman 回测 |
| `engine/calendar.py` | 农业季、播种网格、农业季资格判定 |
| `engine/et0.py` | 大气层外辐射、Penman–Monteith、Hargreaves 备选方法 |
| `engine/crop.py` | 四阶段 Kc 曲线、开花敏感窗口 |
| `engine/slot.py` | SCS-CN 径流、逐日水分平衡、热量与霜冻因子、产量 |
| `engine/table.py` | 带记忆化的槽位表；循环平滑仅用于选择播种日期 |
| `engine/rotation.py` | 轮作有效性、种植模式、P 与 I 指数、歉收季、指标 |
| `engine/soil.py` | 土壤健康评分（氮、多样性、侵蚀防护、有机质） |
| `engine/climate.py` | 气候方案、前后期比较、Mann–Whitney U |
| `engine/alternatives.py` | 方案枚举与方案选择，附带有据可查的放宽规则 |
| `engine/cards.py` | 基于模板的推荐卡片 |

引擎约定（[AGENTS.md](../../../AGENTS.md)）：对农业季使用 numpy 向量化，对日期使用显式循环，`engine/` 中不出现魔法数字。

---

## 4. API

### `POST /analyze`

请求（`AnalyzeRequest`），以示范案例为例：

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

| 字段 | 规则 |
|---|---|
| `lat` / `lon` | `-60 … 60` / `-180 … 180`。取数据前坐标四舍五入到 2 位小数。 |
| `soil_texture` | `arenoso` \| `franco`（默认）\| `arcilloso` |
| `sow_date` | `"MM-DD"`，日必须为 `01` 或 `16`（半月） |
| `years` | 1 到 3 年；每年 1 到 2 个槽位，在农业季内按时间顺序排列 |
| `crop_id` | 必须存在于目录中（小写、无重音符号：`soya`、`maiz` 等） |
| `include_diversified` | **API 默认值：`false`。** 网页界面发送 `true`。 |

错误：
- **422**，`detail` 为西班牙语消息：作物不存在、槽位重叠、收获到下一次播种之间少于 10 天、轮作中没有可收获作物。
- **503**，`detail`：POWER 不可达，且该坐标没有缓存数据。

响应（`AnalyzeResponse`）：

| 键 | 内容 |
|---|---|
| `meta` | 位置、海拔、半球、农业季起点（`07-01` 南半球 / `01-01` 北半球）、农业季列表、时段、Hargreaves 天数比例、分辨率说明、假设 S1–S12 |
| `climate` | 14 个气候指标：前期、近期、差值、p 值、显著性、逐季序列、来源 |
| `climatology` | 从农业季起点起的 24 个半月分箱，分别对应 `before` 和 `recent`（降雨、ET0、Tmax、Tmin） |
| `rotations` | 固定顺序：`actual`、`adaptada`、`regenerativa`，若请求则附加 `diversificada`。每项包含槽位、指标、逐季结果和卡片。 |
| `modis_backtest` | 对象；若该坐标没有本地 MODIS 缓存则为 `null` |

`GET /crops` 返回目录摘要（ID、名称、科、是否可收获、待核实数量）。

缓存：POWER 序列按点保存在磁盘上；完整的 `/analyze` 响应按进程保存在内存中，键为请求体的 SHA-256。

---

## 5. 数据来源

### 5.1 NASA POWER（逐日，点位 API）

- 端点：`https://power.larc.nasa.gov/api/temporal/daily/point`，社区 `AG`（农业气候学）。无需凭据。
- 时间窗口：`19910101`–`20251231`（`DATA_START`、`DATA_END`）。示范样本包含 **12,784 个连续日**（1991-01-01 至 2025-12-31）。
- 磁盘缓存：`backend/cache/power/{lat:.2f}_{lon:.2f}_{start}_{end}.json`（原始响应）。
- 客户端：超时 60 秒；共 3 次尝试（一次请求加两次重试），两次尝试之间先等待 2 秒，再等待 4 秒；最终失败抛出 `PowerUnavailable`。代码的默认重试元组还包含 8 秒，但在 3 次尝试下永远不会用到（见 §13）。
- 海拔：`geometry.coordinates[2]`。

| POWER 参数 | 内部列 | 单位 | 在模型中的作用 |
|---|---|---|---|
| `PRECTOTCORR` | `prec` | mm/日 | 降雨；SCS-CN 径流、水分平衡、气候方案 |
| `T2M_MAX` | `tmax` | °C | ET0、热胁迫、高温日计数 |
| `T2M_MIN` | `tmin` | °C | ET0、霜冻胁迫、GDD |
| `T2M` | `t2m` | °C | 已摄入；按设计 ET0 使用 `(tmax + tmin)/2`（FAO-56 式 6） |
| `RH2M` | `rh` | % | Penman–Monteith 中的水汽压 |
| `ALLSKY_SFC_SW_DWN` | `rs` | MJ/m²/日 | 净辐射（CERES SYN1deg） |
| `WS2M` | `ws` | m/s | Penman–Monteith 中的风速项 |
| `PS` | `ps` | kPa | 干湿表常数 |
| `GWETTOP` | `gwettop` | 0–1 | 已摄入；表层土壤湿度（0–5 cm） |
| `GWETROOT` | `gwetroot` | 0–1 | 土壤湿度合理性检验的参照（§10） |

POWER 参数名只出现在 `nasa/power.py` 和输出中的 `Source.parameters` 里。

### 5.2 NASA MODIS MOD13Q1 v061（仅用于验证）

- 产品：MOD13Q1 v061，250 m，16 天合成，波段 `250m_16_days_NDVI`，比例因子 0.0001，通过 ORNL DAAC 子集 API 获取。
- 仅用于示范点的**离线回测**。`/analyze` 路径从不在网络上请求 MODIS（`offline_only=True`）。
- 采样：每个农业季在夏季窗口取 4 个合成影像（`A{y+1}017` … `A{y+1}065`），20 个农业季 → 80 个合成影像。
- 服务限制：每次请求最多 10 个日期（超过则返回 HTTP 400）。项目实测每次请求耗时 33–42 秒。
- 缓存：`backend/cache/modis/{lat:.2f}_{lon:.2f}_MOD13Q1.json`。测试样本：`backend/tests/fixtures/modis_demo.json`。

---

## 6. 科学模型

完整的规范性说明见 [PLAN.md](../../../PLAN.md) §4，本节为摘要。公式在代码块中给出；常量位于 `config.py`。

### 6.1 农业季（分析单位）

- 若 `lat < 0` 为南半球 `S`，否则为北半球 `N`。农业季 `y` 从 **7 月 1 日**（S）或 **1 月 1 日**（N）开始。聚合从不使用日历年。
- 有效农业季：`inicio(y) − 180 d ≥ DATA_START` 且 `inicio(y) + 365 + 183 d ≤ DATA_END` → **S：1991–2024（34 个）**，**N：1992–2024（33 个）**。
- `before` = 前 15 个农业季（1991/92–2005/06）。`recent` = 后 15 个（2010/11–2024/25）。`eval` = 后 20 个（2005/06–2024/25）。按构造，`before` 与 `eval` 共享 2005/06 农业季。
- 在南半球，月份 ≥ 07 的播种日期落在农业季 `y` 的日历年 `y`；月份 < 07 则落在 `y+1`。这样跨过 12 月 31 日的作物能保持完整。

### 6.2 参考蒸散量（ET0）

Penman–Monteith（FAO-56 式 6），其中 `T = (tmax + tmin)/2`。当缺少 RH、辐射或风速时，**逐日**改用 Hargreaves（FAO-56 式 52）；使用 Hargreaves 的天数比例记录在 `meta.et0_hargreaves_share` 中（示范中为 0.0）。

```
Ra     = (24·60/π)·0.0820·dr·(ωs·sin φ·sin δ + cos φ·cos δ·sin ωs)   MJ m⁻² d⁻¹   （φ 以弧度表示，南纬为负）
ET0_PM = (0.408·Δ·Rn + γ·900/(T+273)·ws·(es − ea)) / (Δ + γ·(1 + 0.34·ws))
ET0_HG = 0.0023·(T + 17.8)·√(tmax − tmin)·Ra·0.408                         （备选；Ra 用 0.408 换算）
```

### 6.3 作物系数与开花窗口

- Kc 在四个阶段（初期、发育期、中期、后期）上分段线性，依据 FAO-56 表 11–12。不根据气候调整 Kc（假设 S3）。
- 敏感窗口（开花）：`[t_mid − 5, t_mid + 25)` 天，其中 `t_mid = L_ini + L_dev`。

### 6.4 逐日单桶水分平衡

- **径流（SCS-CN）：** `S = 25400/CN − 254`；若 `P > 0.2S`，则 `RO = (P − 0.2S)² / (P + 0.8S)`，否则为 0。
- **有效降雨：** 低于 `0.2 × ET0` 的降雨被忽略（`Pe = 0`）。当天降雨在评估胁迫因子**之前**进入土壤。
- **土壤桶：** 容量 `TAW = AWC × Zr`；`AWC` 按质地取 80 / 155 / 160 mm/m，`CN` 取 67 / 78 / 85（arenoso / franco / arcilloso）。
- **胁迫：** `RAW = p·TAW`，其中 `p = clip(p_tab + 0.04·(5 − ETc), 0.1, 0.8)`；若 `D ≤ RAW` 则 `Ks = 1`，否则 `(TAW − D)/(TAW − RAW)`。
- **预热（spin-up）：** 播种前 180 天，从 `Dr = 0.5·TAW` 开始。最后 120 天，若前一槽位在 30 天内收获，则 `Kc = 0.90`（`mode = "crop"`）；否则 `Kc = 0.20`（`mode = "fallow"`）。
- **水分因子：** `f_agua = clip(1 − Ky·(1 − ΣETa/ΣETc), 0, 1)`。比值按总和计算，从不对逐日比值取平均（FAO-56 式 90）。

### 6.5 热量、霜冻因子与相对产量

```
Y_rel = f_agua · f_calor · f_helada · f_temp         ∈ [0, 1]
```

- **f_temp：** 在整个生长周期内，对日均温应用 EcoCrop 梯形响应后取平均。
- **f_calor：** `1 − mean_{敏感窗口}( clip((tmax − Tcrit)/(Tlim − Tcrit), 0, 1) )`。
- **f_helada：** 若开花窗口内任一天 `tmin < t_helada`（0 °C），取 `0.3`；否则若周期内任一天 `tmin < −3 °C`，取 `0.7`；否则为 `1`。假设 S6。
- **限制因子：** 若最小因子低于 0.95，则为该因子；否则为 `ninguno`。平局按 agua、calor、helada、temperatura 的顺序决定。

### 6.6 轮作指数与歉收季

- 槽位构成 1 到 3 年的循环序列。有效性：每次收获到下一次播种的间隔 ≥ 10 天；`sow_offset + 持续时间 ≤ 365 + 183`；至少有一种可收获作物。
- 对每个农业季 `y`，将 `y` 的气候应用于轮作的**每个阶段** `k = 1..L`：

```
P_y = (1/L) · Σ_k Σ_{s ∈ 第 k 年, 可收获} w_s · Y_rel(s, y)
Pot = (1/L) · Σ_k Σ_{s ∈ 第 k 年, 可收获} w_s
I_y = P_y / Pot                  歉收季 ⇔ I_y < 0.60
```

- 覆盖作物（`cosechable = false`）不计入 `P` 和 `Pot`，但计入土壤、种植模式和有效性。
- 在 20 个评估农业季上的指标：`mean_index`、`p10_index`（线性百分位数）、`mean_productivity`、`bad_seasons`（共 20）、`bad_before` 与 `bad_recent`（各共 15），以及 `productivity_vs_current = 100 · mean_P / mean_P(actual)`。
- 当 `Y_rel < 0.50` 时，该槽位在该农业季"失败"。

### 6.7 土壤健康评分（0–100）

```
total = 0.25 · (nitrogen + diversity + erosion + organic_matter)
```

- **氮：** `clip(60 + 20 · N_年, 0, 100)`，其中 `N_年 = (1/L) · Σ_s N_POINTS[class_n(s)]`。分值：`cobertura_leguminosa` +2.0，`leguminosa_grano` +0.5，`cobertura_no_leguminosa` +0.5，`extractiva` −1.0，`muy_extractiva` −1.5。
- **多样性：** `DIVERSITY_BASE[科数] · (1 − 0.5 · 重复比例)`，科数为 1 / 2 / 3 时基数为 30 / 65 / 85，4 科及以上为 100。`重复比例` 是循环相邻作物对中属于同一科的比例。
- **有机质：** `clip(100 · ((1/L) · Σ_s pts(s)) / 6, 0, 100)`，其中 `pts = RESIDUE_POINTS[class]`（bajo 1、medio 2、alto 3），对不可收获覆盖作物再加 `COVER_CROP_BONUS = 1`。
- **侵蚀防护：** 逐日 SCS-CN 径流（评估农业季，按农业季内日序平均），用覆盖曲线加权，以百分比表示。覆盖度为收获后的残茬（`RESIDUE_COVER`：bajo 0.3、medio 0.5、alto 0.8），作物发育期间线性上升，之后为 1.0。假设免耕（S5）。若总径流为 0，则评分为 100。
- 土壤评分**不**反馈影响产量（假设 S4）。

### 6.8 气候方案与显著性检验

每个农业季计算十四个指标（定义见 [PLAN.md](../../../PLAN.md) §4.8）：

- **降雨：** 总量，以及按农业季季度（第 0–90、91–181、182–272、273 天至结束）的分量。
- **雨季开始（onset）：** 第一个偏移量 ≥ 62，使得连续 3 天降雨 ≥ 20 mm，且其后 30 天内没有连续 ≥ 10 天的干旱期（< 1 mm/日）。
- **雨季结束（cessation）：** 第一个偏移量 ≥ 开始 + 60，使得连续 20 天降雨 < 10 mm。
- **雨季长度**、**高温日**（Tmax > 35 °C）、**干旱期**，以及雨季内**最长干旱期**、**GDD**（基温 10 °C）、**ET0 总量**、**水分亏缺**。

对每个指标：计算 `before` 与 `recent` 的均值（忽略 NaN），`delta = recent − before`，双侧 **Mann–Whitney U** 检验的 p 值（若任一样本少于 5 个值则为 `None`），以及 `significant = p < 0.10`。

### 6.9 替代方案

方案选择是确定性的，遵循 [PLAN.md](../../../PLAN.md) §5。放宽的约束记录在 `relaxed_constraints` 中。

| 方案 | 目标 | 约束（放宽前） | 排序 |
|---|---|---|---|
| `actual` | 基线：按输入的轮作，不重新优化 | — | — |
| `adaptada`（适应型） | 最小改动 | 年数和槽位数相同，最多更换一种作物，播种日期重新优化，`mean_P ≥ 当前的 95%` | 歉收季最少 → `p10_index` 最高 → `mean_P` 最高 → 改动最少 |
| `regenerativa`（再生型） | 在限定产量损失下获得最好的土壤 | 土壤增益 ≥ 10 分，`mean_P ≥ 当前的 80%`，歉收季不多于当前 | 土壤总分最高 → `mean_P` 最高 |
| `diversificada`（多样化，可选） | 两年多样化循环 | ≥ 3 个科，≥ 3 种可收获作物，土壤不低于当前 | 歉收季不多于当前的方案中 `mean_P` 最高 |

放宽顺序：`regenerativa` 的损失上限 20% → 30%；取消歉收季限制；土壤增益 10 → 1 分。若无候选满足条件，`adaptada` 会取消其产量过滤。

### 6.10 推荐卡片

卡片由固定模板生成，而非自由文本。每个模板仅在条件满足时触发，并引用其数字所依据的参数。测试断言：论断文本中的每个数字都出现在其 `evidence[].value` 中（PLAN §2.5）。卡片包含三部分：**原因**、**收益**和**风险**。

---

## 7. 作物目录

目录（[backend/app/data/crops.json](../../../backend/app/data/crops.json)）包含 13 种作物。下表数值直接读取自该文件。

| ID | 名称 | 科 | 可收获 | 阶段 ini/dev/mid/late（天） | Kc ini/mid/end | Zr（m） | p | Ky | EcoCrop Tmin/Topt-min/Topt-max/Tmax（°C） | 热胁迫 Tcrit/Tlim（°C） | 氮类别 | 残茬 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `soya` | 大豆 | Fabaceae | 是 | 20/30/60/25 | 0.40/1.15/0.50 | 1.0 | 0.50 | 0.85 | 10/20/33/38 | 35/40 | leguminosa_grano | bajo |
| `maiz` | 玉米 | Poaceae | 是 | 25/40/45/30 | 0.30/1.20/0.35 | 1.3 | 0.55 | 1.25 | 10/18/33/47 | 35/45 | muy_extractiva | alto |
| `sorgo` | 高粱 | Poaceae | 是 | 20/35/40/30 | 0.30/1.05/0.55 | 1.5 | 0.55 | 0.90 | 8/22/35/40 | 35/40 | extractiva | alto |
| `trigo` | 小麦 | Poaceae | 是 | 15/25/50/30 | 0.30/1.15/0.30 | 1.2 | 0.55 | 1.15 | 5/15/23/27 | 27/40 | extractiva | medio |
| `girasol` | 向日葵 | Asteraceae | 是 | 25/35/45/25 | 0.35/1.10/0.35 | 1.2 | 0.45 | 0.95 | 5/17/34/45 | 34/45 | muy_extractiva | medio |
| `frijol` | 菜豆 | Fabaceae | 是 | 20/30/40/20 | 0.40/1.15/0.35 | 0.7 | 0.45 | 1.15 | 7/16/25/32 | 25/32 | leguminosa_grano | bajo |
| `mani` | 花生 | Fabaceae | 是 | 25/35/45/25 | 0.40/1.15/0.60 | 0.8 | 0.50 | 0.70 | 10/22/32/45 | 32/45 | leguminosa_grano | bajo |
| `algodon` | 棉花 | Malvaceae | 是 | 30/50/55/45 | 0.35/1.15/0.60 | 1.4 | 0.65 | 0.85 | 15/22/36/42 | 36/42 | muy_extractiva | bajo |
| `cebada` | 大麦 | Poaceae | 是 | 15/25/50/30 | 0.30/1.15/0.25 | 1.2 | 0.55 | 1.15 | 2/15/20/40 | 20/40 | extractiva | medio |
| `papa` | 马铃薯 | Solanaceae | 是 | 25/30/45/30 | 0.50/1.15/0.75 | 0.5 | 0.35 | 1.10 | 7/15/25/30 | 25/30 | extractiva | bajo |
| `mijo` | 小米 | Poaceae | 是 | 15/25/40/25 | 0.30/1.00/0.30 | 1.5 | 0.55 | 0.90 | 12/25/35/40 | 35/40 | extractiva | alto |
| `avena_cob` | 燕麦（覆盖） | Poaceae | **否** | 15/25/45/5 | 0.30/1.15/1.15 | 1.2 | 0.55 | 1.00 | 5/16/20/30 | 20/30 | cobertura_no_leguminosa | alto |
| `crotalaria` | 猪屎豆（覆盖） | Fabaceae | **否** | 15/25/45/5 | 0.40/1.10/1.10 | 1.0 | 0.50 | 1.00 | 15/23/30/37 | 30/37 | cobertura_leguminosa | alto |

覆盖作物截断为 90 天的周期，Kc_end = Kc_mid（假设 S9）。Teixeira 等人（2013）未涵盖的作物，其热胁迫阈值由 EcoCrop 推导（S7）。所有作物的霜冻阈值 `t_helada` 为 0 °C（S6）。

---

## 8. 示范地点的结果

示范点：**圣克鲁斯，玻利维亚（−17.30, −62.25），海拔 280.15 m**，质地 `franco`（AWC 155 mm/m，CN 78）。当前轮作：大豆 11-16 + 大豆 05-01。以下所有数值均读取自 [frontend/public/demo_santa_cruz.json](../../../frontend/public/demo_santa_cruz.json)。

### 8.1 气候变化（前期 1991/92–2005/06 与近期 2010/11–2024/25）

| 指标 | 单位 | 前期 | 近期 | 差值 | p 值 | 显著（p < 0.10） |
|---|---|---|---|---|---|---|
| 总降雨 | mm/农业季 | 1342.0 | 1146.0 | −195.9 | 0.0114 | 是 |
| 降雨，第 1 季度 | mm | 145.4 | 142.7 | −2.73 | 0.9669 | 否 |
| 降雨，第 2 季度 | mm | 466.2 | 287.9 | −178.3 | 0.0006 | 是 |
| 降雨，第 3 季度 | mm | 493.3 | 436.6 | −56.64 | 0.2290 | 否 |
| 降雨，第 4 季度 | mm | 237.3 | 279.1 | +41.79 | 0.2455 | 否 |
| 雨季开始 | 偏移量（天） | 82.6 | 110.2 | +27.6 | 0.0016 | 是 |
| 雨季结束 | 偏移量（天） | 312.9 | 274.8 | −38.12 | 0.0723 | 是 |
| 雨季长度 | 天 | 232.1 | 168.0 | −64.1 | 0.0055 | 是 |
| 高温日（Tmax > 35 °C） | 天/农业季 | 52.73 | 80.47 | +27.73 | 0.0084 | 是 |
| 干旱期（≥ 10 天） | 次数 | 1.00 | 1.73 | +0.73 | 0.0791 | 是 |
| 最长干旱期 | 天 | 11.00 | 13.47 | +2.47 | 0.0828 | 是 |
| GDD（基温 10 °C） | °C·天 | 5694 | 5934 | +240.4 | 0.0202 | 是 |
| ET0 总量 | mm/农业季 | 1522 | 1587 | +65.02 | 0.1057 | **否** |
| 水分亏缺 | mm/农业季 | 470.7 | 659.0 | +188.3 | 0.0101 | 是 |

14 个指标中有 10 个显著。其余 4 个（第 1、3、4 季度降雨，以及 ET0 总量）不显著，如实报告。

### 8.2 轮作方案（评估窗口，20 个农业季）

| 方案 | 轮作（第 1 年 · 第 2 年） | I 均值 | I P10 | 相对当前产量 | 歉收季 | 土壤总分 | N | 多样性 | 侵蚀防护 | 有机质 |
|---|---|---|---|---|---|---|---|---|---|---|
| `actual` | soya@11-16 + soya@05-01 | 0.7644 | 0.6812 | 100.00 % | 1 / 20 | 47.90 | 80.0 | 15.0 | 63.26 % | 33.33 |
| `adaptada` | mijo@11-16 + soya@03-16 | 0.8589 | 0.7779 | 112.36 % | 0 / 20 | 63.82 | 50.0 | 65.0 | 73.60 % | 66.67 |
| `regenerativa` | crotalaria@10-16 + sorgo@02-16 · girasol@11-01 + mijo@04-16 | 0.8795 | 0.8277 | 86.30 % | 0 / 20 | 79.03 | 45.0 | 85.0 | 86.12 % | 100.00 |
| `diversificada` | algodon@09-16 + sorgo@04-01 · mijo@11-16 + girasol@03-16 | 0.8819 | 0.7958 | 115.37 % | 0 / 20 | 60.56 | 10.0 | 74.38 | 82.88 % | 75.00 |

当前轮作中最差的农业季：**2016/17**（I = 0.5541，限制因子：热）、**2023/24**（I = 0.6796，水分）、**2015/16**（I = 0.6814，水分）。

`adaptada` 替换一种作物（大豆 → 小米），并在同一一年结构内重新优化播种日期。`regenerativa` 和 `diversificada` 是两年循环。`regenerativa` 的土壤评分最高；`diversificada` 的产量最高，但氮评分最低（10.0），因为它不含豆科作物。

### 8.3 卫星验证（MODIS MOD13Q1，离线）

- 夏季 NDVI 最大值与当前轮作的模拟指数 `I` 之间的 Spearman 秩相关：**ρ = −0.0617，p = 0.7962**（n = 20）。没有显著相关。按计算结果报告。
- NDVI 下三分位阈值：**0.7260**。唯一的歉收季 2016/17 的 NDVI 最大值为 **0.7160**，因此落在下三分位内（**1 / 1** 个歉收季）。

解读：一个 250 m 像元反映的是每年该地块实际种植的作物，而模型模拟的是一个由约 50 km 区域气候驱动的固定轮作。在正常年份，两者不应期待密切相关。

---

## 9. 前端

技术栈：Vite、React 19、严格模式的 TypeScript、Leaflet（`react-leaflet`）、Recharts。**界面标签为西班牙语。** 标识符和代码为英文。

| 区域 | 组件 | 功能 |
|---|---|---|
| 地块与轮作（a） | `views/MapForm.tsx`、`components/RotationEditor.tsx` | Leaflet 地图，点击获取坐标；质地选择器；按半月设置的轮作编辑器，带重叠与间隔校验；圣克鲁斯示范按钮 |
| 气候变化（b） | `views/ClimateShift.tsx`、`components/MetricDelta.tsx` | 每个气候指标一张卡片（前期 → 近期、差值，p ≥ 0.10 时显示"No significativo"），逐季序列，NASA 来源 |
| 日历 | `components/CalendarChart.tsx` | 24 个半月的降雨与 ET0 图表，Tmax/Tmin 线，作物阶段条及高亮的开花窗口 |
| 比较（c） | `views/Compare.tsx`、`components/CompareTable.tsx`、`components/RotationCard.tsx`、`components/ModisBacktestCard.tsx` | 方案并排对比，20 个农业季的歉收季条带，含“为什么 / 收益 / 风险”的卡片，每个论断的证据标签，MODIS 卡片 |
| API 客户端 | `src/api.ts`、`src/types.ts` | 调用 `/analyze` 与 `/crops`；回退到预缓存示范数据和静态作物列表；`types.ts` 手工镜像 `schemas.py` |

当数据来自预缓存文件时，顶部栏会显示**离线示范**提示。

---

## 10. 验证与测试

- **后端测试套件：** `pytest -q` → **159 passed, 1 warning**，在开发机上约 3 分钟。测试离线运行：使用 `backend/tests/fixtures/` 中的样本或 `httpx.MockTransport`。
- **前端：** `npm run build` 以严格模式运行 `tsc`，然后执行 Vite 构建。
- **Go/no-go 检查**（[PLAN.md](../../../PLAN.md) §3，N1–N2），位于 [notebooks/01_validacion_motor.ipynb](../../../notebooks/01_validacion_motor.ipynb)：
  1. 年 ET0 在 1,100 至 2,000 mm 之间，年降雨在 700 至 1,800 mm 之间。
  2. 夏季大豆的产量高于冬季大豆。
  3. 当前轮作的歉收季在 20 个中占 1 至 15 个。
  4. 将最差的三个农业季与报道的干旱事件进行比对。
  5. 模拟的 `1 − Dr/TAW` 与 `gwetroot` 的相关系数高于 0.5。这是**合理性检查，不是独立验证**，因为两者使用相同的降雨。

  本文档编写过程中**未重新运行**该 notebook。项目早期文档中报告的结果（包括检查 5 的 r = 0.5501）未在此重新计算。

---

## 11. 假设与局限

以下是 [PLAN.md](../../../PLAN.md) §4.10 中的假设 S1–S12，它们也出现在 `meta.assumptions` 中。

- **S1** POWER 是约 50 km 分辨率的再分析（MERRA-2），辐射为 1°（CERES）。它描述的是区域气候，而不是特定地块。模拟的 Tmax 往往低于气象站读数，因此高于 35 °C 的天数统计偏保守。
- **S2** 初始水分：180 天预热，固定 Kc 为 0.20（休闲）或 0.90（前作）。不模拟真实的前作。
- **S3** 物候按日历天计算。Kc 不根据湿度或风速调整。不考虑光周期。
- **S4** 土壤评分不改变模拟产量。
- **S5** 假定为免耕管理。
- **S6** 霜冻为阶跃规则：开花期因子 0.3，营养期因子 0.7。
- **S7** Teixeira 等人（2013）未涵盖的热胁迫阈值由 EcoCrop 推导。
- **S8** 氮与残茬类别是一般农艺知识，而非测量结果。
- **S9** 覆盖作物采用类比参数、截断的 90 天周期，不产生籽粒收获。
- **S10** 产量相对于农业生态潜力。没有价格，也没有利润。默认所有作物 `value_weight = 1`。
- **S11** 单层土壤桶模型。未模拟的内容包括：渍水、病虫害、杂草、出苗失败、地下水、毛细上升、养分动态，以及土壤结构随时间的变化。
- **S12** 再分析中的降雨趋势可能包含观测系统的伪影。因此报告 p 值，并在 `p ≥ 0.10` 时标注"不显著"。

由这些假设导出的范围限制：
- 引擎每次请求评估一个点。区域比较需要对每个坐标各发一次请求。
- 输出是在固定轮作模板下的相对排序。它既不是产量预测，也不是季节性预报。
- 土壤评分与产量相互独立：更高的土壤评分不会提高模拟产量。

---

## 12. 仓库结构

```
.
├── README.md                     # 本文件（英文主版本）
├── AGENTS.md                     # 贡献者与智能体的工程规则
├── PLAN.md                       # 规范性计划：契约（§2）、公式（§4）、测试（§6）
├── docs/i18n/
│   ├── es/README.md              # Español
│   ├── pt-BR/README.md           # Português (Brasil)
│   └── zh-CN/README.md           # 中文（简体）
├── backend/
│   ├── pyproject.toml            # 依赖与开发额外项（pytest）
│   ├── app/
│   │   ├── main.py               # FastAPI 端点、CORS、错误处理
│   │   ├── pipeline.py           # analyze()：编排与进程内缓存
│   │   ├── schemas.py            # Pydantic v2 契约
│   │   ├── config.py             # 引擎的全部常量
│   │   ├── data/                 # crops.json 及其加载器
│   │   ├── nasa/                 # power.py（POWER 客户端）、modis.py（MODIS 回测）
│   │   └── engine/               # 纯函数：calendar、et0、crop、slot、table、
│   │                             #   rotation、soil、climate、alternatives、cards
│   ├── scripts/                  # 规范的数据脚本（见 §13）
│   └── tests/                    # test_*.py 与 fixtures/
├── frontend/
│   ├── package.json · vite.config.ts · tsconfig.json · index.html
│   ├── public/demo_santa_cruz.json   # 预缓存的离线示范
│   └── src/                      # App.tsx、api.ts、types.ts、views/、components/
├── notebooks/01_validacion_motor.ipynb
└── contracts/analyze_response.example.json
```

由 git 生成并忽略：`backend/cache/`、`backend/.venv/`、`frontend/node_modules/`、`frontend/dist/`。

---

## 13. 已知问题

- **脚本重复。** 仓库根目录的 `scripts/` 与 `backend/scripts/` 同时存在，且内容不同。本文档中的命令使用 `backend/scripts/`，视为规范版本。根目录的副本在核对之前已过时。
- **缺失文件。** [AGENTS.md](../../../AGENTS.md) 和 [PLAN.md](../../../PLAN.md) 将 `QUESTIONS.md` 作为未决问题的记录位置。该文件不在仓库中。
- **没有许可证文件。** 仓库未声明许可证，因此未定义复用条款。
- **多样化方案的默认值因客户端而异。** API 默认 `include_diversified: false`；网页界面发送 `true`。
- **冷缓存。** 没有 `backend/cache/` 时，新坐标的首次 `/analyze` 需要联网访问 POWER。`frontend/public/` 中的预缓存示范可离线使用。界面会提示首次查询可能需要约 20 秒。
- **开发代理覆盖范围。** Vite 代理只转发 `/analyze` 和 `/crops`，不转发 `/health`。若要从其他来源调用后端，请设置 `VITE_API_URL`。
- **MODIS 范围。** MODIS 回测是预缓存的，按设计为离线运行。没有本地 MODIS 缓存的坐标无法运行该回测，此时 `modis_backtest` 字段为 `null`。
- **POWER 重试与计划不一致。** [PLAN.md](../../../PLAN.md) §2.3 规定三次重试，等待时间为 2、4、8 秒。[backend/app/nasa/power.py](../../../backend/app/nasa/power.py) 实际为共 3 次尝试（2 次重试），等待时间为 2 秒和 4 秒。以代码行为为准；计划尚未更新。

---

## 14. 文档与翻译

- **本文件的英文版是主版本。** [docs/i18n/](../../) 中的西班牙语、巴西葡萄牙语和简体中文版本均由其翻译而来。
- 公式、代码块、标识符、作物 ID、POWER 与 MODIS 参数名、文件路径以及 API 字段名在四个版本中完全相同。
- 译文为人工维护。修改本文件时，应在同一次变更中同步更新译文。

---

## 15. 术语表

| 术语 | 含义 |
|---|---|
| 农业季（*campaña*） | 从 7 月 1 日（S）或 1 月 1 日（N）开始的农业年。分析单位。 |
| 槽位（slot） | 一种作物及其播种日期和种植模式：（作物，播种日期，`crop` \| `fallow`） |
| 模式（mode） | 若前一次收获在播种前 30 天内，则为 `crop`，否则为 `fallow` |
| TAW | 根区总有效水分（mm） |
| RAW | 易利用水分，`p · TAW`（mm） |
| Dr | 根区亏缺量（mm） |
| Y_rel | 某槽位在某农业季的相对产量，0–1 |
| P、Pot、I | 轮作在某农业季的生产力、潜力与指数 |
| 歉收季（Bad season） | `I < 0.60` 的农业季 |
| 评估窗口（Eval window） | 最近 20 个农业季，用于所有主要指标 |

---

## 16. 参考文献

- Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements.* FAO Irrigation and Drainage Paper 56.
- Doorenbos, J., & Kassam, A. H. (1979). *Yield response to water.* FAO Irrigation and Drainage Paper 33（产量响应系数 Ky 的来源）。
- USDA Soil Conservation Service. *National Engineering Handbook, Section 4 (Hydrology)*，以及 TR-55（径流曲线数方法）。
- Teixeira, E. I., 等人（2013）。*Global and Planetary Change*（热胁迫阈值）。
- FAO ECOCROP 数据库（温度适宜范围）。
- NASA POWER（Prediction Of Worldwide Energy Resources），Langley Research Center。数据集 MERRA-2 与 CERES SYN1deg。
- MODIS MOD13Q1 v061，250 m，16 天 NDVI，通过 ORNL DAAC 子集 API 获取。
