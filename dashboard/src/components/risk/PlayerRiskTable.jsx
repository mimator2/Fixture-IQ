import { useState, useMemo } from "react";
import { usePlayerRisks } from "@/hooks/usePlayerRisks";
import { Link } from "react-router-dom";
import RiskBadge from "./RiskBadge";
import FlagBadge from "./FlagBadge";
import { ChevronRight, Search } from "lucide-react";
import { Input } from "@/components/ui/input";

const BANDS = ["All Labels", "Low", "Medium", "High", "Very High"];
const ROLES = ["All Roles", "Core Starter", "Rotation Player"];
const POSITIONS = ["All Positions", "Defender", "Midfielder", "Forward"];

export default function PlayerRiskTable() {
  const [search, setSearch] = useState("");
  const [band, setBand] = useState("All Labels");
  const [role, setRole] = useState("All Roles");
  const [position, setPosition] = useState("All Positions");
  const [team, setTeam] = useState("All Teams");

  const { data: players = [], isLoading, error } = usePlayerRisks();

  const teams = useMemo(() => {
    const t = [...new Set(players.map(p => p.team_name).filter(Boolean))];
    return t.sort();
  }, [players]);

  const filtered = players.filter(p => {
    const matchSearch = !search || p.player_name?.toLowerCase().includes(search.toLowerCase()) || p.team_name?.toLowerCase().includes(search.toLowerCase());
    const matchBand = band === "All Labels" || p.risk_band === band;
    const matchRole = role === "All Roles" || p.player_role === role;
    const matchPos = position === "All Positions" || p.position === position;
    const matchTeam = team === "All Teams" || p.team_name === team;
    return matchSearch && matchBand && matchRole && matchPos && matchTeam;
  });

  const sorted = [...filtered].sort((a, b) => {
    const order = { "Very High": 0, "High": 1, "Medium": 2, "Low": 3 };
    return (order[a.risk_band] ?? 4) - (order[b.risk_band] ?? 4);
  });

  const [openFilter, setOpenFilter] = useState(null);


  if (isLoading) return (
    <div className="space-y-3">
      {[1,2,3,4,5].map(i => <div key={i} className="bg-card border border-border rounded-xl h-16 animate-pulse" />)}
    </div>
  );
  if (error) return (
    <div className="bg-card border border-destructive/50 rounded-xl p-6 text-center">
      <p className="text-destructive font-semibold text-sm">Failed to load player data</p>
      <p className="text-muted-foreground text-xs mt-1">{error.message}</p>
    </div>
  );

  return (
     <div>
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search player or team..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
        </div>
        {[
          { label: "Team", options: ["All Teams", ...teams], value: team, set: setTeam },
          { label: "Risk", options: BANDS, value: band, set: setBand },
          { label: "Role", options: ROLES, value: role, set: setRole },
          { label: "Position", options: POSITIONS, value: position, set: setPosition },
        ].map(f => (
          <div key={f.label} className="relative">
            <button
              type="button"
              onClick={() => setOpenFilter(openFilter === f.label ? null : f.label)}
              className="bg-background border border-border/60 rounded-md px-3 py-2 text-sm text-foreground/80 focus:outline-none focus:ring-1 focus:ring-ring/50 transition-colors min-w-[140px] text-left flex items-center justify-between"
            >
              <span>{f.value}</span>
              <span className="text-muted-foreground text-xs ml-2">▾</span>
            </button>
            {openFilter === f.label && (
              <div className="absolute top-full left-0 mt-1 bg-background border border-border/60 rounded-md shadow-lg z-50 max-h-[220px] overflow-y-auto pr-2 pb-8
                [&::-webkit-scrollbar]:w-[3px]
                [&::-webkit-scrollbar-track]:bg-transparent
                [&::-webkit-scrollbar-thumb]:bg-muted-foreground/30
                [&::-webkit-scrollbar-thumb]:rounded-full">
                {f.options.map(o => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => { f.set(o); setOpenFilter(null); }}
                    className={`block w-full text-left px-3 py-1.5 text-sm transition-colors ${
                      f.value === o ? "text-foreground bg-muted/50" : "text-foreground/70 hover:text-foreground hover:bg-muted/30"
                    }`}
                  >
                    {o}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="text-xs text-muted-foreground mb-3">{sorted.length} player{sorted.length !== 1 ? "s" : ""} shown</div>

      <div className="space-y-2">
        {sorted.map(player => (
          <Link key={player.id} to={`/player/${player.id}`}
            className="flex items-center gap-4 bg-card border border-border rounded-xl px-4 py-3 hover:border-primary/30 transition-colors group">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-sm">{player.player_name}</span>
                <span className="text-xs text-muted-foreground">{player.team_name}</span>
                <span className="text-xs text-muted-foreground">·</span>
                <span className="text-xs text-muted-foreground">{player.position}</span>
                {player.player_role && (
                  <span className="text-xs px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">{player.player_role}</span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(player.risk_flags || []).map(f => <FlagBadge key={f} flag={f} />)}
              </div>
            </div>

            <div className="flex items-center gap-4 shrink-0">
              <div className="text-left hidden sm:block min-w-[5rem]">
                <div className="text-xs text-muted-foreground">Risk Score</div>
                <div className="text-sm font-semibold text-primary">{player.fatigue_score?.toFixed(3) ?? "—"}</div>
              </div>
              <RiskBadge band={player.risk_band} />
              <div className="text-left hidden lg:block max-w-48">
                <div className="text-xs text-muted-foreground">{player.recommended_action}</div>
              </div>
              <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </Link>
        ))}

        {sorted.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">No players match the current filters.</div>
        )}
      </div>
    </div>
  );
}
