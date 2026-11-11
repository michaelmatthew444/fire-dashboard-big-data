import React, { useState, useEffect, useMemo } from "react"

import Speedometer from "./speedometer.jsx"

export default function WeatherCard({ data }) {
  // Destructure weather card object properties
  const { label, unit, current, min, avg, max } = data;

  return (
    <div className="flex flex-col justify-between rounded-xl border border-gray-800 bg-gray-900/90 p-5 shadow-lg backdrop-blur transition-all hover:border-gray-700">
      {/* CARD TITLE USING THE "key" PROPERTY DIRECTLY */}
      <div className="mb-2 text-center text-sm font-semibold tracking-wide text-gray-300 uppercase">
        {label}
      </div>

      {/* SPEEDOMETER GAUGE */}
      <div className="my-2 flex justify-center">
        <Speedometer current={current} min={min} max={max} unit={unit} />
      </div>

      {/* FOOTER METRICS: MIN, AVG, MAX */}
      <div className="mt-4 grid grid-cols-3 gap-1 rounded-lg bg-gray-950/60 p-2 text-center text-xs">
        <div className="border-r border-gray-800 pr-1">
          <div className="text-[10px] font-semibold text-gray-500 uppercase">Min</div>
          <div className="font-semibold text-blue-400">{min ?? "N/A"}</div>
        </div>
        <div className="border-r border-gray-800 px-1">
          <div className="text-[10px] font-semibold text-gray-500 uppercase">Avg</div>
          <div className="font-semibold text-yellow-500">{avg ?? "N/A"}</div>
        </div>
        <div className="pl-1">
          <div className="text-[10px] font-semibold text-gray-500 uppercase">Max</div>
          <div className="font-semibold text-red-400">{max ?? "N/A"}</div>
        </div>
      </div>
    </div>
  );
}