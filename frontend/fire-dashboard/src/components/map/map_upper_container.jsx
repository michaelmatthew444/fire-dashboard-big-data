import React from "react";

export default function MapUpperContainer({ mode, toggleMode, onRefresh, children }) {
  return (
    <div className="w-full flex items-center gap-4 bg-gray-900 p-4 text-white">
      {/* Refresh button on the left */}
      <button 
        onClick={onRefresh}
        className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium transition"
      >
        Refresh
      </button>

      {/* Toggle button between historic and forecast */}
      <button 
        onClick={toggleMode}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium transition capitalize"
      >
        {mode}
      </button>

      {/* Remaining space: Temperature gradient bar (270K to 367K) */}
      <div className="flex-1 flex flex-col justify-center">
        <div className="flex justify-between text-xs mb-1 text-gray-300">
          <span>270 K</span>
          <span>Temperature Scale</span>
          <span>367 K</span>
        </div>
        <div 
          className="h-4 w-full rounded"
          style={{ background: "linear-gradient(to right, #22c55e, #eab308, #ef4444)" }}
        />
      </div>

      {children}
    </div>
  );
}