import { useQuery } from "@tanstack/react-query";

export function usePlayerTimeline(playerId) {
  return useQuery({
    queryKey: ["player-timeline", playerId],
    queryFn: async () => {
      const res = await fetch(`/data/player_timelines/${playerId}.json`);
      if (!res.ok) return [];
      return res.json();
    },
    enabled: !!playerId,
    staleTime: 300_000,
  });
}
