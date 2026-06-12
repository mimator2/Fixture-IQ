import { useQuery } from "@tanstack/react-query";

const fetchJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url} (${res.status})`);
  return res.json();
};

export function useCongestionMetrics() {
  return useQuery({
    queryKey: ["congestion-metrics"],
    queryFn: () => fetchJson("/data/congestion_metrics.json"),
    staleTime: 300_000,
    retry: 2,
  });
}
