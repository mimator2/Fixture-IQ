import { useQuery } from "@tanstack/react-query";

const fetchJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url} (${res.status})`);
  return res.json();
};

export function usePlayerTimeline(playerId) {
  return useQuery({
    queryKey: ["playerTimeline", playerId],
    queryFn: () => fetchJson(`/data/player_timelines/${playerId}.json`),
    staleTime: 5 * 60 * 1000,
    retry: 1,
    enabled: !!playerId,
  });
}
