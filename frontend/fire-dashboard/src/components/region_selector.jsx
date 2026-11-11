import React from "react";

export default function RegionSelect({ 
  regions = [], 
  selectedRegionId, 
  onChangeRegion, 
  title = "Current Weather" 
}) {
  const regionOptions = Array.isArray(regions) && regions.length > 0 
    ? regions 
    : [1, 2, 3, 4, 5];

  return (
    <div className="mt-10 mb-6 flex items-center justify-between w-full">
      {/* Title placed on the left side of the page */}
      <h2 className="text-xl font-bold tracking-wide text-white">
        {title}
      </h2>

      {/* Region ID Dropdown Select on the right side */}
      <select
        value={selectedRegionId}
        onChange={(e) => onChangeRegion(Number(e.target.value))}
        className="cursor-pointer rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-sm font-semibold text-white shadow-md transition-all hover:border-blue-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
      >
        {regionOptions.map((reg) => {
          const id = typeof reg === "object" ? reg.region_id : reg;
          return (
            <option key={id} value={id} className="bg-gray-900 text-white">
              Region {id}
            </option>
          );
        })}
      </select>
    </div>
  );
}