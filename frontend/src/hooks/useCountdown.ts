import { useEffect, useRef, useState } from 'react';

/**
 * A hard countdown: ticks once per second while `active`, fires `onElapsed`
 * exactly once at zero. Pure timer logic, unit-tested with fake timers.
 */
export function useCountdown(active: boolean, seconds: number, onElapsed: () => void): number {
  const [remaining, setRemaining] = useState(seconds);
  const elapsedRef = useRef(onElapsed);
  elapsedRef.current = onElapsed;

  useEffect(() => {
    if (!active) return undefined;
    setRemaining(seconds);
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      const left = Math.max(0, seconds - Math.floor((Date.now() - startedAt) / 1000));
      setRemaining(left);
      if (left <= 0) {
        window.clearInterval(timer);
        elapsedRef.current();
      }
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [active, seconds]);

  return remaining;
}
