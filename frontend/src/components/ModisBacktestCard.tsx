import React, { useId, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Cell,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import type { ModisBacktestOut, ModisSeasonPoint } from "../types";

interface ModisBacktestCardProps {
  backtest: ModisBacktestOut;
}

interface CustomTooltipPayloadItem {
  payload?: ModisSeasonPoint;
}

interface ModisTooltipProps {
  active?: boolean;
  payload?: CustomTooltipPayloadItem[];
}

const formatPValue = (pValue: number): string => {
  if (!Number.isFinite(pValue)) return "—";
  if (pValue < 0.0001) return pValue.toExponential(2);
  return pValue.toFixed(4);
};

const ModisTooltip: React.FC<ModisTooltipProps> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0 || !payload[0].payload) {
    return null;
  }

  const point = payload[0].payload;

  return (
    <div className="modis-tooltip" role="status">
      <div className="modis-tooltip-title">Campaña {point.label}</div>
      <div className="modis-tooltip-row">
        <span>NDVI máximo estival (MODIS):</span>
        <strong>{point.max_ndvi.toFixed(3)}</strong>
      </div>
      <div className="modis-tooltip-row">
        <span>Índice simulado RotaClima (I):</span>
        <strong>
          {(point.sim_index * 100).toFixed(1)}% ({point.sim_index.toFixed(3)})
        </strong>
      </div>
      <div className="modis-tooltip-flags">
        <span className={`badge ${point.bad ? "badge-danger" : "badge-success"}`}>
          {point.bad ? "Campaña mala simulada" : "Campaña normal simulada"}
        </span>
        <span className={`badge ${point.in_low_tertile ? "badge-warning" : "badge-neutral"}`}>
          {point.in_low_tertile ? "En tercil inferior NDVI" : "Fuera de tercil inferior"}
        </span>
      </div>
    </div>
  );
};

export const ModisBacktestCard: React.FC<ModisBacktestCardProps> = ({ backtest }) => {
  const [showDataTable, setShowDataTable] = useState<boolean>(false);
  const headingId = useId();
  const chartDescId = useId();
  const tableWrapperId = useId();
  const tableCaptionId = useId();

  const ndviValues = backtest.series.map((s) => s.max_ndvi).filter(Number.isFinite);
  const minNdvi = ndviValues.length > 0 ? Math.min(...ndviValues, backtest.tertile_threshold) : 0;
  const maxNdvi = ndviValues.length > 0 ? Math.max(...ndviValues, backtest.tertile_threshold) : 1;
  const ndviDomainMin = Math.max(0, Math.floor((minNdvi - 0.05) * 20) / 20);
  const ndviDomainMax = Math.min(1, Math.ceil((maxNdvi + 0.05) * 20) / 20);

  const getBarColor = (point: ModisSeasonPoint): string => {
    if (point.bad && point.in_low_tertile) return "#dc2626";
    if (point.in_low_tertile) return "#d97706";
    if (point.bad) return "#e11d48";
    return "#0284c7";
  };

  return (
    <article className="modis-backtest-card card" aria-labelledby={headingId}>
      <header className="modis-card-header">
        <div className="modis-header-main">
          <div className="modis-badge-row">
            <span className="badge badge-info">🛰️ Evidencia Satelital Independiente</span>
            <span className="badge badge-outline">{backtest.n_seasons} campañas evaluadas</span>
          </div>
          <h3 id={headingId} className="modis-card-title">
            Validación Satelital Independiente — NASA MODIS (MOD13Q1 • 250 m)
          </h3>
          <p className="modis-card-subtitle">
            Contraste empírico directo entre el índice simulado por RotaClima (línea base actual) y el pico estival de verdor observado en superficie (NDVI).
          </p>
        </div>
      </header>

      <div className="modis-card-content">
        {/* 3 KPIs */}
        <div className="modis-kpi-grid" role="list" aria-label="Indicadores de validación MODIS">
          <div className="modis-kpi-item" role="listitem">
            <span className="modis-kpi-label">Correlación de rangos de Spearman (ρ)</span>
            <strong className="modis-kpi-value">{backtest.spearman_rho.toFixed(3)}</strong>
            <span className="modis-kpi-meta">
              p-valor = {formatPValue(backtest.p_value)}
            </span>
            <span className="modis-kpi-note">
              Resultado empírico mostrado tal cual sin calibración forzada
            </span>
          </div>

          <div className="modis-kpi-item" role="listitem">
            <span className="modis-kpi-label">Campañas malas en tercil inferior NDVI</span>
            <strong className="modis-kpi-value">
              {backtest.bad_in_low_ndvi_tertile} de {backtest.total_bad_seasons}
            </strong>
            <span className="modis-kpi-meta">
              Umbral tercil inferior: NDVI ≤ {backtest.tertile_threshold.toFixed(3)}
            </span>
            <span className="modis-kpi-note">
              Coincidencia entre caídas simuladas de rendimiento y menor vigor vegetal satelital
            </span>
          </div>

          <div className="modis-kpi-item" role="listitem">
            <span className="modis-kpi-label">Escala espacial contrastada</span>
            <strong className="modis-kpi-value modis-kpi-scale">
              250 m (píxel local MODIS) vs ~50 km (reanálisis POWER)
            </strong>
            <span className="modis-kpi-meta">
              {backtest.n_seasons} campañas evaluadas en ventana de contraste
            </span>
            <span className="modis-kpi-note">
              Diferencia de resolución entre clima regional y respuesta puntual de lote
            </span>
          </div>
        </div>

        {/* Chart */}
        <figure className="modis-chart-figure" aria-describedby={chartDescId}>
          <div className="modis-chart-legend-bar">
            <span className="modis-legend-chip">
              <span className="modis-swatch modis-swatch-normal" aria-hidden="true" />
              NDVI normal
            </span>
            <span className="modis-legend-chip">
              <span className="modis-swatch modis-swatch-tertile" aria-hidden="true" />
              NDVI en tercil inferior (≤ {backtest.tertile_threshold.toFixed(3)})
            </span>
            <span className="modis-legend-chip">
              <span className="modis-swatch modis-swatch-both" aria-hidden="true" />
              Campaña mala y tercil inferior
            </span>
          </div>

          <div className="modis-chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart
                data={backtest.series}
                margin={{ top: 16, right: 20, left: 4, bottom: 16 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  tickLine={false}
                  axisLine={{ stroke: "#cbd5e1" }}
                  interval="preserveStartEnd"
                  angle={-30}
                  textAnchor="end"
                  height={48}
                />
                <YAxis
                  yAxisId="ndvi"
                  orientation="left"
                  domain={[ndviDomainMin, ndviDomainMax]}
                  tickFormatter={(v: number) => v.toFixed(2)}
                  tick={{ fontSize: 11, fill: "#0369a1" }}
                  axisLine={{ stroke: "#cbd5e1" }}
                  tickLine={false}
                  label={{
                    value: "NDVI máx.",
                    angle: -90,
                    position: "insideLeft",
                    style: { fill: "#0369a1", fontSize: 11, fontWeight: 600 },
                  }}
                />
                <YAxis
                  yAxisId="index"
                  orientation="right"
                  domain={[0, 1]}
                  tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                  tick={{ fontSize: 11, fill: "#0f766e" }}
                  axisLine={{ stroke: "#cbd5e1" }}
                  tickLine={false}
                  label={{
                    value: "Índice simulado (I)",
                    angle: 90,
                    position: "insideRight",
                    style: { fill: "#0f766e", fontSize: 11, fontWeight: 600 },
                  }}
                />
                <Tooltip content={<ModisTooltip />} />
                <Legend
                  verticalAlign="top"
                  height={32}
                  wrapperStyle={{ fontSize: "12px" }}
                />
                {Number.isFinite(backtest.tertile_threshold) && (
                  <ReferenceLine
                    yAxisId="ndvi"
                    y={backtest.tertile_threshold}
                    stroke="#d97706"
                    strokeDasharray="5 4"
                    strokeWidth={1.5}
                    label={{
                      value: `Tercil inferior NDVI (${backtest.tertile_threshold.toFixed(3)})`,
                      position: "insideTopLeft",
                      fill: "#b45309",
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  />
                )}
                <Bar
                  yAxisId="ndvi"
                  dataKey="max_ndvi"
                  name="NDVI máximo estival (MODIS)"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={28}
                >
                  {backtest.series.map((entry) => (
                    <Cell key={`cell-${entry.season}`} fill={getBarColor(entry)} />
                  ))}
                </Bar>
                <Line
                  yAxisId="index"
                  type="monotone"
                  dataKey="sim_index"
                  name="Índice simulado RotaClima (I)"
                  stroke="#0f766e"
                  strokeWidth={2.5}
                  dot={{ r: 3.5, fill: "#0f766e", stroke: "#ffffff", strokeWidth: 1.5 }}
                  activeDot={{ r: 5.5 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <figcaption id={chartDescId} className="modis-chart-caption">
            Serie de {backtest.n_seasons} campañas comparando el NDVI máximo estival observado por MODIS (barras, eje izquierdo) frente al índice de rendimiento simulado por RotaClima (línea verde, eje derecho), con la línea de referencia del tercil inferior en {backtest.tertile_threshold.toFixed(3)}.
          </figcaption>
        </figure>

        {/* Accessible semantic data table alternative */}
        <div className="modis-table-toggle-row">
          <button
            type="button"
            className="btn btn-outline btn-sm"
            aria-expanded={showDataTable}
            aria-controls={tableWrapperId}
            onClick={() => setShowDataTable((prev) => !prev)}
          >
            {showDataTable
              ? "Ocultar tabla de datos por campaña"
              : "Ver tabla de datos MODIS por campaña"}
          </button>
        </div>

        {showDataTable && (
          <div
            id={tableWrapperId}
            tabIndex={0}
            role="region"
            aria-labelledby={tableCaptionId}
            className="modis-table-wrapper"
          >
            <table className="modis-data-table">
              <caption id={tableCaptionId}>
                Detalle por campaña de NDVI máximo MODIS e índice simulado RotaClima ({backtest.n_seasons} campañas)
              </caption>
              <thead>
                <tr>
                  <th scope="col">Campaña</th>
                  <th scope="col">NDVI máximo</th>
                  <th scope="col">Índice simulado (I)</th>
                  <th scope="col">Campaña mala simulada</th>
                  <th scope="col">Tercil inferior NDVI</th>
                </tr>
              </thead>
              <tbody>
                {backtest.series.map((point) => (
                  <tr key={point.season}>
                    <th scope="row">{point.label}</th>
                    <td>{point.max_ndvi.toFixed(3)}</td>
                    <td>
                      {(point.sim_index * 100).toFixed(1)}% ({point.sim_index.toFixed(3)})
                    </td>
                    <td>{point.bad ? "Sí" : "No"}</td>
                    <td>{point.in_low_tertile ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <footer className="modis-card-footer">
        <span className="source-cite">
          <strong>Fuente satelital:</strong> {backtest.source.dataset} |{" "}
          <strong>Banda / Parámetros:</strong> {backtest.source.parameters.join(", ")} |{" "}
          <strong>Período:</strong> {backtest.source.period}
        </span>
      </footer>
    </article>
  );
};
