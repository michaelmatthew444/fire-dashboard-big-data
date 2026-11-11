import React from "react";
import { title, subtitle, owner } from "../constants/variables";

export function Title({ children }) {
  return <>
    <p>{owner}</p>
    <h1 className="mt-[16px] text-[36px] font-bold tracking-[-1.68px] text-[var(--text-h)] lg:my-[20px] lg:text-[56px]">{title}</h1>
    <h2 className="mb-[32px]">{subtitle}</h2>

  </>;
}
