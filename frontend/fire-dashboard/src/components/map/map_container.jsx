import React, { useState, useEffect, useMemo } from "react";
import MapUpperContainer from "./map_upper_container.jsx";
import MapBottomSlider from "./map_bottom_slider.jsx";
import { FireMap } from "./map.jsx";


export default function MapContainer({mode, toggleMode, onRefresh, data, selectedIndex, selectedDate, dates, onDateChange,  mapDataLoading, mapDataError}){


    return (
        <>
            <MapUpperContainer
                mode = {mode}
                toggleMode = {toggleMode}
                onRefresh = {onRefresh}
            />
            
            {mapDataLoading ? (
                <div className="flex h-[550px] w-full items-center justify-center rounded-t-md bg-gray-900 text-gray-300 font-medium">
                Loading map data...
                </div>
            ) : mapDataError ? (
                <div className="flex h-[550px] w-full items-center justify-center rounded-t-md bg-gray-900 text-red-500 font-medium">
                Error loading map data: {mapDataError}
                </div>
            ) : (
                <FireMap 
                data={data} 
                mode={mode} 
                selectedIndex={selectedIndex}
                selectedDate={selectedDate}
                />
            )}

            <MapBottomSlider
                dates = {dates}
                selectedIndex = {selectedIndex}
                onDateChange = {onDateChange}
            />
        </>
    );
}

