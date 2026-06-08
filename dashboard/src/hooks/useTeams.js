import { useQuery } from "@tanstack/react-query";

const fetchJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url} (${res.status})`);
  return res.json();
};

export function useTeams() {
  return useQuery({
    queryKey: ["teams"],
    queryFn: () => fetchJson("/data/teams.json"),
    staleTime: 300_000,
    retry: 2,
  });
}

export function useTeam(teamId) {
  const { data: teams = [] } = useTeams();
  return useQuery({
    queryKey: ["team", teamId],
    queryFn: () => {
      const t = teams.find(t => t.id === teamId);
      if (!t) throw new Error(`Team "${teamId}" not found`);
      return t;
    },
    enabled: !!teamId && teams.length > 0,
    staleTime: 300_000,
  });
}
