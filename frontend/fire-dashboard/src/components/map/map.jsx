// FireMap.jsx
import React, { useEffect, useState, useMemo } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Helper component to auto-fit map view to GeoJSON boundaries
function FitBounds({ data }) {
  const map = useMap();
  useEffect(() => {
    if (data) {
      const bounds = L.geoJSON(data).getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    }
  }, [data, map]);
  return null;
}

/**
 * Maps a numeric value linearly into an RGB Green-to-Red hex/rgb color string.
 */
function getGreenToRedColor(value, min, max) {
  if (value === null || value === undefined) return "#22c55e"; // Default Green

  // Clamp value between min and max bounds
  const clampedVal = Math.max(min, Math.min(max, value));
  const ratio = (clampedVal - min) / (max - min); // 0.0 to 1.0

  // Calculate RGB transition: Green (34, 197, 94) -> Red (239, 68, 68)
  const r = Math.round(34 + ratio * (239 - 34));
  const g = Math.round(197 - ratio * (197 - 68));
  const b = Math.round(94 - ratio * (94 - 68));

  return `rgb(${r}, ${g}, ${b})`;
}

export function FireMap({ data, mode = "historical", selectedIndex = 0, selectedDate = null }) {
  const [geoData, setGeoData] = useState(null);
  const [error, setError] = useState(null);

  // 1. Fetch map.geojson from the public directory[cite: 2]
  useEffect(() => {
    fetch("/map.geojson")
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        try {
          return JSON.parse(text);
        } catch {
          throw new Error(
            "map.geojson is not valid JSON. Starts with: " + text.slice(0, 60)
          );
        }
      })
      .then(setGeoData)
      .catch((err) => {
        console.error("GeoJSON Load Error:", err);
        setError(err.message);
      });
  }, []);

  // 2. Build a fast Map lookup for region_id -> API record item[cite: 2]
  const dataLookup = useMemo(() => {
    const mapLookup = new Map();
    const rawList = Array.isArray(data) ? data : data?.data || [];

    rawList.forEach((item) => {
      if (item?.region_id !== undefined && item?.region_id !== null) {
        mapLookup.set(Number(item.region_id), item);
      }
    });

    return mapLookup;
  }, [data]);

  // 3. Helper to determine region color based on active mode
  const getFeatureColor = (regionId) => {
    const record = dataLookup.get(Number(regionId));
    if (!record) return "#22c55e"; // Default Green if no data exists

    if (mode === "historical") {
      // Historical: bright_ti4 between 270K (Green) and 367K (Red)
      const temp = record.bright_ti4 ?? 270;
      return getGreenToRedColor(temp, 270, 367);
    } else {
      // Forecast: fire_risk_score between 0.0 (Green) and 1.0 (Red)
      const riskScore = record.fire_risk_score ?? 0;
      return getGreenToRedColor(riskScore, 0.0, 1.0);
    }
  };

  // 4. Style function for GeoJSON polygons
  const styleFeature = (feature) => {
    const props = feature.properties || {};
    const regionId = props.region_id ?? props.id ?? props.OBJECTID ?? props.objectid;
    const color = getFeatureColor(regionId);

    return {
      fillColor: color,
      weight: 1.5,
      opacity: 0.8,
      color: "#ffffff", // White border outline
      fillOpacity: 0.65,
    };
  };

  // 5. Attach Hover Tooltips & Mouseover/Mouseout Cleanups[cite: 1, 2, 3]
  const onEachFeature = (feature, layer) => {
    const props = feature.properties || {};
    const regionId = props.region_id ?? props.id ?? props.OBJECTID ?? props.objectid;
    const regionName = props.namobj || props.NAME || `Region ${regionId}`;
    const record = dataLookup.get(Number(regionId));

    // Construct Hover Tooltip HTML Content[cite: 3]
    let tooltipContent = `<div class="p-2 font-sans text-xs">`;
    tooltipContent += `<div class="font-bold text-sm text-gray-900 border-b pb-1 mb-1">${regionName} (ID: ${regionId})</div>`;

    if (mode === "historical") {
      if (record) {
        tooltipContent += `
          <div><span class="font-semibold">Acquisition Date:</span> ${record.acq_date || "N/A"}</div>
          <div><span class="font-semibold">Acquisition Time:</span> ${record.acq_time || "N/A"}</div>
          <div><span class="font-semibold">Bright TI4 (Temp):</span> <span class="text-red-600 font-bold">${record.bright_ti4 ?? "N/A"} K</span></div>
          <div><span class="font-semibold">Bright TI5:</span> ${record.bright_ti5 ?? "N/A"} K</div>
          <div><span class="font-semibold">FRP (Fire Power):</span> ${record.frp ?? "N/A"} MW</div>
          <div><span class="font-semibold">Day/Night:</span> ${record.daynight === "D" ? "Day" : "Night"}</div>
        `;
      } else {
        tooltipContent += `<div class="text-gray-500 italic">No active hotspot records for this date (Default: Green).</div>`;
      }
    } else {
      // Forecast Mode[cite: 3]
      if (record) {
        const riskScorePercent = ((record.fire_risk_score || 0) * 100).toFixed(1);
        tooltipContent += `
          <div><span class="font-semibold">Forecast Timestamp:</span> ${record.forecast_timestamp || "N/A"}</div>
          <div><span class="font-semibold">Fire Risk Score:</span> <span class="font-bold text-red-600">${riskScorePercent}% (${record.fire_risk_score?.toFixed(3)})</span></div>
          <div><span class="font-semibold">Fire Predicted:</span> ${record.is_fire_predicted === 1 ? "YES (High Risk)" : "NO (Low Risk)"}</div>
        `;
      } else {
        tooltipContent += `<div class="text-gray-500 italic">No forecast data for this date (Risk: 0.0 / Green).</div>`;
      }
    }

    tooltipContent += `</div>`;

    // Bind Leaflet Tooltip
    layer.bindTooltip(tooltipContent, {
      sticky: true,
      direction: "auto",
      className: "custom-leaflet-tooltip shadow-lg rounded border border-gray-200 bg-white opacity-95",
    });

    // Handle Hover Highlighting & Clean Reset
    layer.on({
      mouseover: (e) => {
        const polygon = e.target;
        polygon.setStyle({
          weight: 3,
          color: "#000000",
          fillOpacity: 0.85,
        });
        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
          polygon.bringToFront();
        }
      },
      mouseout: (e) => {
        const polygon = e.target;
        // Use Leaflet native resetStyle to clear hover state instantly without sticky bugs[cite: 1]
        if (e.target._map) {
          const geoJsonLayer = e.target._eventParents
            ? Object.values(e.target._eventParents)[0]
            : null;

          if (geoJsonLayer && typeof geoJsonLayer.resetStyle === "function") {
            geoJsonLayer.resetStyle(polygon);
            return;
          }
        }
        // Fallback safety style reset
        polygon.setStyle(styleFeature(feature));
      },
    });
  };

  if (error) {
    return (
      <div className="p-4 text-red-600 bg-red-50 rounded border border-red-200">
        Error loading map: {error}
      </div>
    );
  }

  if (!geoData) {
    return <div className="p-8 text-center text-gray-400">Loading Map Geometry...</div>;
  }

  return (
    <div className="relative h-[550px] w-full rounded-t-md overflow-hidden shadow-md">
      {/* Active Date Overlay Badge */}
      <div className="absolute top-3 right-3 z-[1000] rounded bg-gray-900/85 px-3 py-1.5 text-xs font-semibold text-white shadow backdrop-blur">
        Mode: <span className="capitalize text-blue-400">{mode}</span> | Date:{" "}
        <span className="text-yellow-400">{selectedDate || "All"}</span> (Index: {selectedIndex})
      </div>

      <MapContainer
        center={[-2.548926, 118.014863]}
        zoom={5}
        className="h-full w-full"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Dynamic Key forces Leaflet layer to re-evaluate styles when date/mode/index changes */}
        {geoData && (
          <GeoJSON
            key={`${mode}-${selectedDate}-${selectedIndex}`}
            data={geoData}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        )}

        <FitBounds data={geoData} />
      </MapContainer>
    </div>
  );
}