import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { SampleSummary } from "../types/analysis";

export function useSamples() {
  const [samples, setSamples] = useState<SampleSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .samples()
      .then(setSamples)
      .catch((err: Error) => setError(err.message));
  }, []);

  return { samples, error };
}
