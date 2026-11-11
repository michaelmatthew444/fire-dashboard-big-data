import React, { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";

// 6 Available Meteorological Metric Configurations
const METEOROLOGY_METRICS = [
  { key: "temperature_2m", label: "Air Temperature (2m)", unit: "°C", color: "#3b82f6" },
  { key: "humidity_2m", label: "Relative Humidity (2m)", unit: "%", color: "#06b6d4" },
  { key: "precipitation", label: "Precipitation", unit: "mm", color: "#6366f1" },
  { key: "wind_speed_10m", label: "Wind Speed (10m)", unit: "km/h", color: "#eab308" },
  { key: "surface_pressure", label: "Surface Pressure", unit: "hPa", color: "#10b981" },
  { key: "cloud_cover", label: "Cloud Cover", unit: "%", color: "#8b5cf6" },
];

export default function WeatherLineGraph({ lineGraphData, currentTime }) {
  // 1. Default selected metric (1 out of 6)
  const [selectedMetricKey, setSelectedMetricKey] = useState("temperature_2m");

  // Determine current active metric object
  const activeMetric = useMemo(() => {
    return (
      METEOROLOGY_METRICS.find((m) => m.key === selectedMetricKey) ||
      METEOROLOGY_METRICS[0]
    );
  }, [selectedMetricKey]);

  // Extract hourly data array safely
  const hourlyData = useMemo(() => {
    return lineGraphData?.hourly_data || [];
  }, [lineGraphData]);

  // 2. Identify Current Time Cutoff (e.g. "11:00")
  const currentHourString = useMemo(() => {
    if (currentTime) return currentTime;
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, "0");
    return `${hours}:00`;
  }, [currentTime]);

  // 3. Compute Gradient Offsets so past (before current time) and forecast (after) render in different colors
  const gradientOffset = useMemo(() => {
    if (!hourlyData || hourlyData.length === 0) return 0;
    const currentIndex = hourlyData.findIndex(
      (item) => item.target_time === currentHourString
    );
    if (currentIndex === -1) return 0.5;
    return currentIndex / (hourlyData.length - 1);
  }, [hourlyData, currentHourString]);

  // Custom Tooltip Renderer
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      const isForecast = dataPoint.target_time > currentHourString;

      return (
        <div className="rounded-lg border border-gray-700 bg-gray-900/95 p-3 shadow-xl backdrop-blur text-xs">
          <div className="font-semibold text-gray-300 mb-1 border-b border-gray-800 pb-1">
            Time: {label} {isForecast ? "(Forecast 🔮)" : "(Recorded 🕒)"}
          </div>
          <div className="flex items-center gap-2">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: isForecast ? "#f97316" : "#3b82f6" }}
            />
            <span className="text-gray-400">{activeMetric.label}:</span>
            <span className="font-bold text-white">
              {payload[0].value} {activeMetric.unit}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  if (!hourlyData || hourlyData.length === 0) {
    return (
      <div className="my-6 flex h-72 w-full items-center justify-center rounded-xl bg-gray-900/50 text-gray-400">
        No hourly line graph data available.
      </div>
    );
  }

  return (
    <div className="my-6 w-full rounded-xl border border-gray-800 bg-gray-900/90 p-5 shadow-lg backdrop-blur">
      {/* Header Container: Title on Left, Metric Selector DDL on Right */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-bold text-white tracking-wide">
            24-Hour Diurnal Weather Trend
          </h3>
          <p className="text-xs text-gray-400">
            Target Date: <span className="text-blue-400">{lineGraphData?.target_date}</span>
          </p>
        </div>

        {/* Selector Dropdown: Select 1 out of 6 Meteo Parameters */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold uppercase text-gray-400">
            Parameter:
          </label>
          <select
            value={selectedMetricKey}
            onChange={(e) => setSelectedMetricKey(e.target.value)}
            className="cursor-pointer rounded-lg border border-gray-700 bg-gray-950 px-3 py-1.5 text-xs font-semibold text-white shadow-md transition-all hover:border-blue-500 focus:border-blue-500 focus:outline-none"
          >
            {METEOROLOGY_METRICS.map((metric) => (
              <option key={metric.key} value={metric.key}>
                {metric.label} ({metric.unit})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Legend Indicator for Past vs Forecast colors */}
      <div className="mb-4 flex items-center justify-end gap-6 text-xs font-medium">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-blue-500" />
          <span className="text-gray-300">Past Observations</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-orange-500" />
          <span className="text-gray-300">Future Forecast</span>
        </div>
      </div>

      {/* Recharts Area/Line Chart */}
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={hourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              {/* Linear Gradient for Split Past/Forecast Fill Colors */}
              <linearGradient id="splitColor" x1="0" y1="0" x2="1" y2="0">
                <stop offset={gradientOffset} stopColor="#3b82f6" stopOpacity={0.8} />
                <stop offset={gradientOffset} stopColor="#f97316" stopOpacity={0.8} />
              </linearGradient>

              {/* Area Background Gradient */}
              <linearGradient id="splitArea" x1="0" y1="0" x2="1" y2="0">
                <stop offset={gradientOffset} stopColor="#3b82f6" stopOpacity={0.25} />
                <stop offset={gradientOffset} stopColor="#f97316" stopOpacity={0.25} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />

            <XAxis
              dataKey="target_time"
              stroke="#6b7280"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "#374151" }}
            />

            <YAxis
              stroke="#6b7280"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: "#374151" }}
              domain={["auto", "auto"]}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Vertical Marker Line for Current Hour */}
            <ReferenceLine
              x={currentHourString}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{
                value: "Now",
                position: "top",
                fill: "#ef4444",
                fontSize: 10,
                fontWeight: "bold",
              }}
            />

            {/* Line / Area rendering active selected parameter */}
            <Area
              type="monotone"
              dataKey={selectedMetricKey}
              stroke="url(#splitColor)"
              strokeWidth={2.5}
              fill="url(#splitArea)"
              dot={{ r: 2, fill: "#3b82f6" }}
              activeDot={{ r: 5, fill: "#ef4444" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}