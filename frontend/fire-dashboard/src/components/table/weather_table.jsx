// components/tables/WeatherTable.jsx
import React from "react";
import DataTable from "./data_table";

export default function WeatherTable({ 
  weatherTableData, 
  page = 1, 
  onPageChange, 
  isLoading 
}) {
  const maxPage = weatherTableData?.max_page || 1;
  const totalItems = weatherTableData?.total_items || 0;
  const data = weatherTableData?.data || [];

  const columns = [
    { key: "weather_id", label: "ID" },
    { key: "acq_date", label: "Acq Date" },
    { key: "acq_time", label: "Acq Time" },
    { 
      key: "temperature_2m", 
      label: "Temp (°C)", 
      render: (val) => <span className="font-semibold text-blue-400">{val != null ? `${val}°C` : "N/A"}</span> 
    },
    { key: "humidity_2m", label: "Humidity (%)", render: (val) => (val != null ? `${val}%` : "N/A") },
    { key: "precipitation", label: "Precip (mm)", render: (val) => (val != null ? `${val} mm` : "N/A") },
    { key: "wind_speed_10m", label: "Wind (km/h)", render: (val) => (val != null ? `${val} km/h` : "N/A") },
    { key: "surface_pressure", label: "Pressure (hPa)", render: (val) => (val != null ? `${val} hPa` : "N/A") },
    { key: "cloud_cover", label: "Cloud (%)", render: (val) => (val != null ? `${val}%` : "N/A") },
    {
      key: "is_forecast",
      label: "Type",
      render: (val) => (
        <span
          className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
            val ? "bg-amber-500/20 text-amber-400" : "bg-emerald-500/20 text-emerald-400"
          }`}
        >
          {val ? "Forecast" : "History"}
        </span>
      ),
    },
  ];

  return (
    <DataTable
      title="Meteorology Table"
      columns={columns}
      data={data}
      page={page}
      maxPage={maxPage}
      totalItems={totalItems}
      onPageChange={onPageChange}
      isLoading={isLoading}
    />
  );
}