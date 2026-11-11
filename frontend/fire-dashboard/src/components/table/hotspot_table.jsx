// components/tables/HotspotTable.jsx
import React from "react";
import DataTable from "./data_table";

export default function HotspotTable({ 
  hotspotTableData,
  page = 1,
  onPageChange,
  isLoading 
}) {
  const maxPage = hotspotTableData?.max_page || 1;
  const totalItems = hotspotTableData?.total_items || 0;
  const data = hotspotTableData?.data || [];

  const columns = [
    { key: "hotspot_id", label: "ID" },
    { key: "acq_date", label: "Acq Date" },
    { key: "acq_time", label: "Acq Time" },
    { 
      key: "bright_ti4", 
      label: "Bright Ti4 (K)", 
      render: (val) => <span className="font-semibold text-red-400">{val ? `${val} K` : "N/A"}</span> 
    },
    { key: "bright_ti5", label: "Bright Ti5 (K)", render: (val) => (val ? `${val} K` : "N/A") },
    { 
      key: "frp", 
      label: "FRP (MW)", 
      render: (val) => <span className="font-semibold text-orange-400">{val ?? "N/A"}</span> 
    },
    {
      key: "daynight",
      label: "Day / Night",
      render: (val) => (
        <span
          className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
            val === "D" ? "bg-yellow-500/20 text-yellow-400" : "bg-indigo-500/20 text-indigo-400"
          }`}
        >
          {val === "D" ? "Day" : "Night"}
        </span>
      ),
    },
  ];

  const handlePageChange = (newPage) => {
    console.log(`[Stub] Fetch Hotspot Table Page: ${newPage}`);
  };

  return (
    <DataTable
      title="Hotspot Table"
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