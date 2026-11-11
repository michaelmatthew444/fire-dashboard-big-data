// api/region_id_fetcher.jsx
import { useState, useEffect } from "react";
import { API_URL } from "../constants/paths";

export function useRegionID(refreshKey) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(`${API_URL}api/data/region`);
        if (!response.ok) throw new Error("Failed to fetch region data");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [refreshKey]); 

  return { RegionIdData: data, RegionIdLoading: loading, RegionIdError: error };
}