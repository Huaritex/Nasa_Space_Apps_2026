import React, { useState, useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from "react-leaflet";
import type { CropSummary, Rotation, SoilTexture } from "../types";
import { RotationEditor } from "../components/RotationEditor";

interface MapFormProps {
  lat: number;
  lon: number;
  soilTexture: SoilTexture;
  currentRotation: Rotation;
  includeDiversified: boolean;
  crops: CropSummary[];
  loading: boolean;
  onLatChange: (lat: number) => void;
  onLonChange: (lon: number) => void;
  onSoilChange: (soil: SoilTexture) => void;
  onRotationChange: (rot: Rotation) => void;
  onIncludeDiversifiedChange: (val: boolean) => void;
  onLoadDemo: () => void;
  onSubmit: () => void;
  validationError: string | null;
}

// Helper component to center map when lat/lon change programmatically
const MapController: React.FC<{ center: [number, number] }> = ({ center }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);
  return null;
};

// Map click listener component
const MapClickHandler: React.FC<{ onLocationSelect: (lat: number, lon: number) => void }> = ({
  onLocationSelect,
}) => {
  useMapEvents({
    click(e) {
      const lat = parseFloat(e.latlng.lat.toFixed(4));
      const lon = parseFloat(e.latlng.lng.toFixed(4));
      onLocationSelect(lat, lon);
    },
  });
  return null;
};

export const MapForm: React.FC<MapFormProps> = ({
  lat,
  lon,
  soilTexture,
  currentRotation,
  includeDiversified,
  crops,
  loading,
  onLatChange,
  onLonChange,
  onSoilChange,
  onRotationChange,
  onIncludeDiversifiedChange,
  onLoadDemo,
  onSubmit,
  validationError,
}) => {
  const markerRef = useRef<any>(null);

  const [latStr, setLatStr] = useState<string>(String(lat));
  const [lonStr, setLonStr] = useState<string>(String(lon));

  // Synchronize string state when lat or lon prop changes externally (e.g. map click, drag, demo load)
  useEffect(() => {
    const parsed = parseFloat(latStr);
    if (isNaN(parsed) || parsed !== lat) {
      setLatStr(String(lat));
    }
  }, [lat]);

  useEffect(() => {
    const parsed = parseFloat(lonStr);
    if (isNaN(parsed) || parsed !== lon) {
      setLonStr(String(lon));
    }
  }, [lon]);

  const handleLatChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    // Allow empty string, "-", or valid floating point numbers
    if (val === "" || val === "-" || /^-?\d*\.?\d*$/.test(val)) {
      setLatStr(val);
      const parsed = parseFloat(val);
      if (!isNaN(parsed)) {
        onLatChange(parsed);
      }
    }
  };

  const handleLatBlur = () => {
    const parsed = parseFloat(latStr);
    if (isNaN(parsed)) {
      setLatStr(String(lat));
    } else {
      setLatStr(String(parsed));
    }
  };

  const handleLonChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    // Allow empty string, "-", or valid floating point numbers
    if (val === "" || val === "-" || /^-?\d*\.?\d*$/.test(val)) {
      setLonStr(val);
      const parsed = parseFloat(val);
      if (!isNaN(parsed)) {
        onLonChange(parsed);
      }
    }
  };

  const handleLonBlur = () => {
    const parsed = parseFloat(lonStr);
    if (isNaN(parsed)) {
      setLonStr(String(lon));
    } else {
      setLonStr(String(parsed));
    }
  };

  const handleDemoClick = () => {
    setLatStr("-17.3");
    setLonStr("-62.25");
    onLoadDemo();
  };

  const handleSubmit = () => {
    const pLat = parseFloat(latStr);
    const pLon = parseFloat(lonStr);
    if (isNaN(pLat) || isNaN(pLon)) {
      setLatStr(String(lat));
      setLonStr(String(lon));
    } else {
      if (pLat !== lat) onLatChange(pLat);
      if (pLon !== lon) onLonChange(pLon);
    }
    onSubmit();
  };

  const markerPosition = useMemo<[number, number]>(() => [lat, lon], [lat, lon]);

  const eventHandlers = useMemo(
    () => ({
      dragend() {
        const marker = markerRef.current;
        if (marker != null) {
          const pos = marker.getLatLng();
          const newLat = parseFloat(pos.lat.toFixed(4));
          const newLon = parseFloat(pos.lng.toFixed(4));
          setLatStr(String(newLat));
          setLonStr(String(newLon));
          onLatChange(newLat);
          onLonChange(newLon);
        }
      },
    }),
    [onLatChange, onLonChange]
  );

  return (
    <div className="map-form-view">
      <div className="view-header">
        <h2 className="page-title">Parcela y Esquema de Rotación</h2>
        <p className="page-description">
          Ubique su lote agrícola en el mapa o ingrese las coordenadas geográficas. Seleccione el tipo de suelo
          y configure la rotación que utiliza habitualmente para evaluar su vulnerabilidad climática contra 34 campañas de datos satelitales NASA POWER.
        </p>
      </div>

      {validationError && (
        <div className="alert alert-danger" role="alert">
          <div className="alert-icon">⚠️</div>
          <div className="alert-content">
            <strong>Error de validación agronómica:</strong>
            <p>{validationError}</p>
          </div>
        </div>
      )}

      <div className="map-form-grid">
        {/* Left Column: Geographic Location & Map */}
        <div className="location-section card">
          <div className="card-header">
            <h3 className="section-title">Ubicación Geográfica</h3>
            <button
              type="button"
              className="btn btn-outline btn-sm btn-demo"
              onClick={handleDemoClick}
              title="Cargar coordenadas y rotación de Santa Cruz, Bolivia (-17.30, -62.25)"
            >
              ⭐ Cargar demo Santa Cruz
            </button>
          </div>

          <div className="map-wrapper">
            <MapContainer
              center={markerPosition}
              zoom={9}
              scrollWheelZoom={true}
              className="leaflet-map-container"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapController center={markerPosition} />
              <MapClickHandler
                onLocationSelect={(newLat, newLon) => {
                  setLatStr(String(newLat));
                  setLonStr(String(newLon));
                  onLatChange(newLat);
                  onLonChange(newLon);
                }}
              />
              <Marker
                draggable={true}
                eventHandlers={eventHandlers}
                position={markerPosition}
                ref={markerRef}
              />
            </MapContainer>
          </div>

          <div className="coords-inputs-row">
            <div className="form-group flex-1">
              <label className="form-label" htmlFor="lat-input">
                Latitud (°):
              </label>
              <input
                id="lat-input"
                type="text"
                inputMode="decimal"
                className="form-input"
                value={latStr}
                onChange={handleLatChange}
                onBlur={handleLatBlur}
                placeholder="-60.0 a 60.0"
              />
              <span className="form-help">Entre -60.0° y 60.0°</span>
            </div>

            <div className="form-group flex-1">
              <label className="form-label" htmlFor="lon-input">
                Longitud (°):
              </label>
              <input
                id="lon-input"
                type="text"
                inputMode="decimal"
                className="form-input"
                value={lonStr}
                onChange={handleLonChange}
                onBlur={handleLonBlur}
                placeholder="-180.0 a 180.0"
              />
              <span className="form-help">Entre -180.0° y 180.0°</span>
            </div>
          </div>

          <div className="form-group" style={{ marginTop: "16px" }}>
            <label className="form-label">Textura del Suelo (Capacidad de Almacenaje):</label>
            <div className="soil-buttons-group">
              {(["arenoso", "franco", "arcilloso"] as SoilTexture[]).map((texture) => (
                <button
                  key={texture}
                  type="button"
                  className={`btn-soil-option ${soilTexture === texture ? "active" : ""}`}
                  onClick={() => onSoilChange(texture)}
                >
                  <span className="soil-name">
                    {texture === "arenoso"
                      ? "Arenoso"
                      : texture === "franco"
                      ? "Franco (Equilibrado)"
                      : "Arcilloso (Pesado)"}
                  </span>
                  <span className="soil-desc">
                    {texture === "arenoso"
                      ? "Baja retención de agua (TAW menor)"
                      : texture === "franco"
                      ? "Retención hídrica media recomendada"
                      : "Alta retención, drenaje más lento"}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="diversified-checkbox-row" style={{ marginTop: "16px" }}>
            <label className="checkbox-label" htmlFor="include-diversified-check">
              <input
                id="include-diversified-check"
                type="checkbox"
                checked={includeDiversified}
                onChange={(e) => onIncludeDiversifiedChange(e.target.checked)}
              />
              <span>
                <strong>Incluir alternativa diversificada</strong> (evalúa 4 perfiles incluyendo rotación de máxima diversidad botánica).
              </span>
            </label>
          </div>
        </div>

        {/* Right Column: Rotation Editor & Submit */}
        <div className="rotation-section">
          <RotationEditor
            rotation={currentRotation}
            onChange={onRotationChange}
            crops={crops}
          />

          <div className="submit-section card" style={{ marginTop: "20px" }}>
            <div className="submit-content">
              <div>
                <h4 style={{ margin: "0 0 6px 0", color: "#1e293b" }}>Simular Desempeño Agroclimático</h4>
                <p style={{ margin: 0, fontSize: "0.9rem", color: "#64748b" }}>
                  Compara la rotación ingresada con ~34 campañas climáticas de NASA POWER e identifica alternativas adaptadas.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary btn-lg"
                onClick={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner-border" />
                    Simulando NASA POWER...
                  </>
                ) : (
                  "Analizar rotación"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
