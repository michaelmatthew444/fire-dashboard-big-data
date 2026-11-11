// mapControlsLogic.js
import { useState } from "react";

export function useMapControls() {
  const [mode, setMode] = useState("historical");

  const handleReset = () => {
    console.log("Refresh/Reset clicked");
    // Add your refresh logic here (e.g., re-fetching data)
  };

  const toggleMode = () => {
    setMode((prevMode) => (prevMode === "historical" ? "forecast" : "historical"));
  };

  return { mode, toggleMode, handleReset };
}