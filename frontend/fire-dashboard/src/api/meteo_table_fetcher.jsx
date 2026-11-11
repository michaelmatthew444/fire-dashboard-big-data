// hooks/useMeteoTable.js
import { useState, useEffect } from "react";
import { API_URL } from "../constants/paths";

export function useMeteoTable(regionId, page) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!regionId || page === undefined || page === null) return;

    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `${API_URL}api/data/table/meteorology?region_id=${regionId}&page=${page}&page_size=10`
        );
        if (!response.ok) throw new Error("Failed to fetch weather table data");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [regionId, page]);

  return {
    MeteorologyTableData: data,
    MeteorologyTableLoading: loading,
    MeteorologyTableError: error,
  };
}