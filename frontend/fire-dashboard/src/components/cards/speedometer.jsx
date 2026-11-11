import React from "react";

export default function Speedometer({ current, min, max, unit }) {
  const safeCurrent = current ?? 0;
  const safeMin = min ?? 0;
  const safeMax = max ?? 100;

  // Calculate position ratio between 0 and 1
  const range = safeMax - safeMin;
  const ratio = range > 0 ? Math.max(0, Math.min(1, (safeCurrent - safeMin) / range)) : 0;

  // Convert ratio (0.0 -> 1.0) to arc rotation angle (-90deg to +90deg)
  const angle = -90 + ratio * 180;

  return (
    <div className="relative flex flex-col items-center justify-center">
      <svg className="h-24 w-44 overflow-visible" viewBox="0 0 100 55">
        {/* Semi-circle Gauge Outer Track */}
        <path
          d="M 10 50 A 40 40 0 0 1 90 50"
          fill="none"
          stroke="#374151"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Dynamic Highlight Progress Arc */}
        <path
          d="M 10 50 A 40 40 0 0 1 90 50"
          fill="none"
          stroke="url(#gauge-gradient)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray="125.6"
          strokeDashoffset={125.6 * (1 - ratio)}
          className="transition-all duration-700 ease-out"
        />
        {/* Needle Indicator */}
        <g transform="translate(50, 50)">
          <line
            x1="0"
            y1="0"
            x2="0"
            y2="-32"
            stroke="#ef4444"
            strokeWidth="2.5"
            strokeLinecap="round"
            transform={`rotate(${angle})`}
            className="transition-transform duration-700 ease-out"
          />
          <circle cx="0" cy="0" r="4" fill="#ef4444" />
        </g>
        {/* Color Gradient Definition */}
        <defs>
          <linearGradient id="gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="50%" stopColor="#eab308" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>
      </svg>
      {/* Current Reading Display */}
      <div className="-mt-3 text-center">
        <span className="text-xl font-bold text-white">{safeCurrent}</span>
        <span className="ml-1 text-xs text-gray-400">{unit}</span>
      </div>
    </div>
  );
}