// components/games/OddsFlashCell.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "../../lib/utils";

interface OddsFlashCellProps {
  value: string | number;
  className?: string;
  /** Optional: force the flash direction */
  forceDirection?: "up" | "down" | null;
}

export default function OddsFlashCell({
  value,
  className,
  forceDirection = null,
}: OddsFlashCellProps) {
  const prevValue = useRef<string | number>(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (prevValue.current === value) return;

    // Determine direction
    let direction: "up" | "down" | null = forceDirection;

    if (!direction) {
      const prev = Number(prevValue.current);
      const next = Number(value);

      if (!Number.isNaN(prev) && !Number.isNaN(next)) {
        if (next > prev) direction = "up";
        else if (next < prev) direction = "down";
      }
    }

    if (direction) {
      setFlash(direction);
      const timer = setTimeout(() => setFlash(null), 700);
      prevValue.current = value;
      return () => clearTimeout(timer);
    }

    prevValue.current = value;
  }, [value, forceDirection]);

  return (
    <span
      className={cn(
        "inline-block rounded px-1.5 py-0.5 transition-colors tabular-nums",
        flash === "up" && "flash-up",
        flash === "down" && "flash-down",
        className
      )}
    >
      {value}
    </span>
  );
}