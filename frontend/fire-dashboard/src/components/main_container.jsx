import React, { useState, useEffect, useMemo } from "react";
import { Title } from "./title.jsx";
import { FireMap } from "./map/map.jsx";
import { useRegionID } from "../api/region_id_fetcher.jsx";
import { useMapData } from "../api/map_fetcher.jsx";
import { useDetailedData } from "../api/data_fetcher.jsx";
import { useMeteoTable } from "../api/meteo_table_fetcher.jsx";
import { useHotspotTable } from "../api/hotspot_table_fetcher.jsx";
import MapUpperContainer from "./map/map_upper_container.jsx";
import MapBottomSlider from "./map/map_bottom_slider.jsx";
import RegionSelect from "./region_selector.jsx";
import CardContainer from "./cards/card_container.jsx";
import WeatherLineGraph from "./weather_line_graph.jsx";
import WeatherTable from "./table/weather_table.jsx";
import HotspotTable from "./table/hotspot_table.jsx";

export default function MainContainer({ children }) {
  // 1. State Declarations (MUST come first to prevent initialization order errors)
  const [mode, setMode] = useState("historical"); // "historical" or "forecast"
  const [regionId, setRegionId] = useState(1);
  const [selectedPageWeather, setSelectedPageWeather] = useState(1);
  const [selectedPageHotspot, setSelectedPageHotspot] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedDateIndex, setSelectedDateIndex] = useState(0);

  // Automatically reset pagination back to Page 1 whenever regionId changes
  useEffect(() => {
    setSelectedPageWeather(1);
    setSelectedPageHotspot(1);
  }, [regionId]);

  // 2. Custom API Hooks
  // Fetch region metadata list
  const { 
    RegionIdData: regionIdData, 
    loading: RegionIdLoading, 
    error: RegionIdError 
  } = useRegionID(refreshKey);

  // Domain-wide map data (only depends on mode & refreshKey)
  const { 
    MapData: mapData, 
    MapLoading: mapDataLoading, 
    MapError: mapDataError 
  } = useMapData(mode, refreshKey);

  // Detailed regional data (cards, line graph, initial tables)
  const { 
    DetailedData: detailedData, 
    DetailedDataLoading: detailedDataLoading, 
    DetailedDataError: detailedDataError 
  } = useDetailedData(regionId, refreshKey);

  // Dedicated weather table pagination hook (triggers when regionId or page changes)
  const { 
    MeteorologyTableData: paginatedMeteoData, 
    MeteorologyTableLoading: paginatedMeteoLoading 
  } = useMeteoTable(regionId, selectedPageWeather);

  // Dedicated hotspot table pagination hook (triggers when regionId or page changes)
  const {
    HotspotTableData: paginatedHotspotData,
    HotspotTableLoading: paginatedHotspotLoading
  } = useHotspotTable(regionId, selectedPageHotspot);

  // 3. Extract Detailed Sections
  const cardsData = detailedData?.record_cards;
  const lineData = detailedData?.record_line;
  const hotspotTableData = detailedData?.record_hotspot_table;

  // 4. Hybrid Weather Table Data Selector
  const activeWeatherTableData = useMemo(() => {
    if (paginatedMeteoData) {
      return paginatedMeteoData;
    }
    return detailedData?.record_meteorology_table;
  }, [paginatedMeteoData, detailedData]);

  // Hybrid Hotspot Table Data Selector
  const activeHotspotTableData = useMemo(() => {
    if (paginatedHotspotData) {
      return paginatedHotspotData;
    }
    return detailedData?.record_hotspot_table;
  }, [paginatedHotspotData, detailedData]);

  // 5. Extract Raw Hotspot Array Safely
  const rawHotspotList = useMemo(() => {
    if (Array.isArray(mapData)) return mapData;
    if (Array.isArray(mapData?.data)) return mapData.data;
    return [];
  }, [mapData]);

  // 6. Compute Available Date Array for Slider
  const availableDates = useMemo(() => {
    if (mode === "historical") {
      // Historical mode: Always generate fixed 7-day rolling window ending today (8 days inclusive)
      const dates = [];
      const today = new Date();
      for (let i = 7; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        dates.push(d.toISOString().split("T")[0]);
      }
      return dates;
    } else {
      // Forecast mode: Parse timestamps dynamically from dataset
      if (!rawHotspotList || rawHotspotList.length === 0) return [];
      const dates = rawHotspotList
        .map((item) => {
          const ts = item.forecast_timestamp || item.target_date || item.acq_date;
          return ts ? ts.split(" ")[0].split("T")[0] : null;
        })
        .filter(Boolean);

      return Array.from(new Set(dates)).sort();
    }
  }, [rawHotspotList, mode]);

  // Default date index to Today (last index) for historical mode, or 0 for forecast
  useEffect(() => {
    if (mode === "historical" && availableDates.length > 0) {
      setSelectedDateIndex(availableDates.length - 1);
    } else {
      setSelectedDateIndex(0);
    }
  }, [mode, mapData, availableDates]);

  // 7. Filter Map Dataset Based on Slider Date
  const filteredMapData = useMemo(() => {
    if (rawHotspotList.length === 0 || availableDates.length === 0) return mapData;

    const selectedDate = availableDates[selectedDateIndex];
    if (!selectedDate) return mapData;

    const filteredList = rawHotspotList.filter((item) => {
      if (mode === "historical") {
        return item.acq_date === selectedDate;
      } else {
        const itemDate = (item.forecast_timestamp || item.target_date || item.acq_date)
          ?.split(" ")[0]
          ?.split("T")[0];
        return itemDate === selectedDate;
      }
    });

    return Array.isArray(mapData) ? filteredList : { ...mapData, data: filteredList };
  }, [mapData, rawHotspotList, availableDates, selectedDateIndex, mode]);

  // Handlers
  const handleToggleMode = () => {
    setMode((prev) => (prev === "historical" ? "forecast" : "historical"));
  };

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  // Initial Page Load Guard (Only blocks on region list load)
  if (RegionIdLoading) {
    return <p className="p-8 text-center text-white">Loading Map Dashboard...</p>;
  }

  if (RegionIdError) {
    return <p className="p-8 text-center text-red-500">Error loading dashboard metadata.</p>;
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1126px] flex-col border-none bg-[var(--surface)] p-8 text-center">
      <Title />

      {/* Map Upper Controls */}
      <MapUpperContainer
        mode={mode}
        toggleMode={handleToggleMode}
        onRefresh={handleRefresh}
      />

      {/* Map View with Inline Loader Guard */}
      {mapDataLoading ? (
        <div className="flex h-[550px] w-full items-center justify-center rounded-t-md bg-gray-900 font-medium text-gray-300">
          Loading map data...
        </div>
      ) : mapDataError ? (
        <div className="flex h-[550px] w-full items-center justify-center rounded-t-md bg-gray-900 font-medium text-red-500">
          Error loading map data: {mapDataError}
        </div>
      ) : (
        <FireMap 
          data={filteredMapData} 
          mode={mode} 
          selectedIndex={selectedDateIndex}
          selectedDate={availableDates[selectedDateIndex]}
        />
      )}

      {/* Date Range Slider */}
      <MapBottomSlider
        dates={availableDates}
        selectedIndex={selectedDateIndex}
        onDateChange={setSelectedDateIndex}
      />

      {/* Title & Region ID Dropdown Selector */}
      <RegionSelect
        regions={regionIdData?.data}
        selectedRegionId={regionId}
        onChangeRegion={setRegionId}
        title="Current Weather"
      />

      {/* 10 Meteorological Cards Container */}
      <CardContainer
        cardsData={cardsData}
        isLoading={detailedDataLoading}
        error={detailedDataError}
      />

      {/* 24-Hour Diurnal Weather Line Graph */}
      <WeatherLineGraph lineGraphData={lineData} />

      {/* Historical Meteorology Table */}
      <WeatherTable
        weatherTableData={activeWeatherTableData}
        page={selectedPageWeather}
        onPageChange={setSelectedPageWeather}
        isLoading={paginatedMeteoLoading}
      />

      {/* Historical Satellite Hotspot Table */}
      <HotspotTable
        hotspotTableData={activeHotspotTableData}
        page={selectedPageHotspot}
        onPageChange={setSelectedPageHotspot}
        isLoading={paginatedHotspotLoading}
      />

      {children}
    </main>
  );
}