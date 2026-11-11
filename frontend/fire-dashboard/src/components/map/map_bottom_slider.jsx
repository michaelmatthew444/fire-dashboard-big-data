// MapBottomSlider.jsx
import React from "react";

export default function MapBottomSlider({
  dates = [],
  selectedIndex = 0,
  onDateChange,
  children,
}) {
  if (!dates || dates.length === 0) return null;

  const currentDate = dates[selectedIndex] || "";

  return (
    <div className="w-full flex items-center gap-4 bg-gray-900 p-4 text-white rounded-b-md shadow-lg border-t border-gray-800">
      {/* Current Selected Date Display */}
      <div className="min-w-[130px] flex flex-col justify-center">
        <span className="text-xs text-gray-400 uppercase tracking-wider">
          Selected Date
        </span>
        <span className="text-sm font-semibold text-blue-400">
          {currentDate}
        </span>
      </div>

      {/* Date Range Slider */}
      <div className="flex-1 flex flex-col justify-center">
        <div className="flex justify-between text-xs mb-1 text-gray-300 font-mono">
          <span>{dates[0]}</span>
          <span>{dates[dates.length - 1]}</span>
        </div>
        <input
          type="range"
          min={0}
          max={dates.length - 1}
          value={selectedIndex}
          onChange={(e) => onDateChange(Number(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500 hover:accent-blue-400 transition"
        />
      </div>

      {/* Step Buttons */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={selectedIndex === 0}
          onClick={() => onDateChange(Math.max(0, selectedIndex - 1))}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed rounded text-xs font-medium transition cursor-pointer"
        >
          Prev Date
        </button>
        <button
          type="button"
          disabled={selectedIndex === dates.length - 1}
          onClick={() => onDateChange(Math.min(dates.length - 1, selectedIndex + 1))}
          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed rounded text-xs font-medium transition cursor-pointer"
        >
          Next Date
        </button>
      </div>

      {children}
    </div>
  );
}