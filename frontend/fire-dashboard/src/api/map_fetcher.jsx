import { useState, useEffect } from "react";
import { API_URL } from "../constants/paths";

export function useMapData(mode, refreshKey) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const url = `${API_URL}api/hotspots/map?mode=${mode}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch map data");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [mode, refreshKey]);

  useEffect(() => {
    if (data?.data) {
      console.log("Map Data:", data);
    }
  }, [data]);


  return { MapData: data, MapLoading: loading, MapError: error };
}