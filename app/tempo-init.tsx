"use client";
// Import the dev tools and initialize them
import { useEffect } from "react";

export function TempoInit() {
  useEffect(() => {
    const init = async () => {
      if (process.env.NEXT_PUBLIC_TEMPO) {
        const { TempoDevtools } = await import("tempo-devtools");
        TempoDevtools.init();
      }
    }

    init()
  }, []);

  return null;
}