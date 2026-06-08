import { useQuery } from "@tanstack/react-query";

const fetchJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url} (${res.status})`);
  return res.json();
};

export function usePlayerRisks() {
  return useQuery({
    queryKey: ["player-risks"],
    queryFn: () => fetchJson("/data/player_risks.json"),
    staleTime: 300_000,
    retry: 2,
  });
}

export function usePlayerRisk(playerId) {
  const { data: players = [] } = usePlayerRisks();
  return useQuery({
    queryKey: ["player-risk", playerId],
    queryFn: () => {
      const p = players.find(p => p.id === playerId);
      if (!p) throw new Error(`Player "${playerId}" not found`);
      return p;
    },
    enabled: !!playerId && players.length > 0,
    staleTime: 300_000,
  });
}
