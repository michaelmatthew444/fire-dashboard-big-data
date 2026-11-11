import React, { useState, useEffect, useMemo } from "react"

import WeatherCard from "./card.jsx"

export default function CardContainer({cardsData, isLoading, error}){


  if (isLoading) {
    return (
      <div className="my-6 flex h-64 w-full items-center justify-center rounded-xl bg-gray-900/50 text-gray-400">
        Loading cards data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-6 w-full rounded-xl bg-red-950/40 p-4 text-center text-red-400 border border-red-800">
        Error loading cards data: {error}
      </div>
    );
  }

  const cardsList =  useMemo(() => {
    if (cardsData?.cards && Array.isArray(cardsData.cards)) {
      return cardsData.cards;
    }
    return [];
  }, [cardsData]);


  return (

    <div className="my-6 w-full">

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {cardsList.map((card) => (
          <WeatherCard key={card.key} data={card} />
        ))}
      </div>
    </div>
  );
}