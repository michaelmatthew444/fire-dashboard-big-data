import { useState, useEffect } from "react";
import { API_URL } from "../constants/paths";

export function useDetailedData(regionId, refreshKey) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const response = await fetch(`${API_URL}api/data?region_id=${regionId}`);
        if (!response.ok) throw new Error("Failed to fetch data");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [regionId, refreshKey]);

  useEffect(() => {
    if (data) {
      console.log("Detailed Data loaded:", data);
    }
  }, [data]);


  return { 
    DetailedData: data, 
    DetailedDataLoading: loading, 
    DetailedDataError: error 
  };
}