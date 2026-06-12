import { useQuery } from "@tanstack/react-query";
import { Database, BarChart3, Calendar, Users } from "lucide-react";

const SEASON = "2024-25";

const fetchJson = async (url) => {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}`);
  return res.json();
};

function useModelMetadata() {
  return useQuery({
    queryKey: ["model-metadata", "sources"],
    queryFn: () => fetchJson("/data/model_metadata.json"),
    staleTime: 300_000,
  });
}

const sources = [
  {
    name: "FBRef / Opta",
    category: "Performance and Workload",
    icon: BarChart3,
    description: "Player minutes, xG, progressive actions, and detailed performance metrics across all competitions.",
    fields: ["Expected Goals (xG)", "Player Minutes", "Progressive Actions", "Shot Data"],
  },
  {
    name: "Premier League and UEFA",
    category: "Fixture Mapping",
    icon: Calendar,
    description: "Official match logs providing precise dates, times, and competition context to calculate recovery windows.",
    fields: ["Match Dates and Times", "Competition Type", "Home/Away Status", "Recovery Windows"],
  },
  {
    name: "Transfermarkt",
    category: "Squad Context",
    icon: Users,
    description: "Injury records, suspensions, and squad information to distinguish tactical rotation from forced changes.",
    fields: ["Injury Records", "Suspensions", "Squad Size", "Market Values"],
  },
];

const methodology = [
  {
    step: "1",
    title: "Data Collection",
    desc: `Gathering match, performance, and squad data from multiple sources for the season.`,
  },
  {
    step: "2",
    title: "Congestion Metrics",
    desc: "Computing rest days, rolling match counts, and domestic-European overlap sequences.",
  },
  {
    step: "3",
    title: "Performance Analysis",
    desc: "Linking congestion indicators to points, results, xG, goal difference, and squad rotation.",
  },
  {
    step: "4",
    title: "Dashboard Prototype",
    desc: "Visualizing findings in an interactive format for analysts and coaching staff.",
  },
];

export default function DataSources() {
  const { data: metadata } = useModelMetadata();
  const season = metadata?.current_season
    ? `${metadata.current_season}-${String(Number(metadata.current_season) + 1).slice(-2)}`
    : SEASON;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-1">{"Data Sources & Methodology"}</h1>
        <p className="text-muted-foreground">
          The data infrastructure and analytical framework powering the Fixture IQ research
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        {sources.map((source) => {
          const Icon = source.icon;
          return (
            <div key={source.name} className="bg-card border border-border rounded-xl p-5 hover:border-primary/30 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <Icon className="w-5 h-5 text-primary" />
              </div>
              <div className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">{source.category}</div>
              <h3 className="font-semibold mb-2">{source.name}</h3>
              <p className="text-sm text-muted-foreground mb-3 leading-relaxed">{source.description}</p>
              <div className="flex flex-wrap gap-1.5">
                {source.fields.map((f) => (
                  <span key={f} className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mb-10">
        <h2 className="text-xl font-bold mb-4">Methodology Pipeline</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {methodology.map((m, i) => (
            <div key={m.step} className="relative">
              <div className="bg-card border border-border rounded-xl p-5">
                <div className="w-8 h-8 rounded-full bg-primary/15 flex items-center justify-center text-sm font-bold text-primary mb-3">
                  {m.step}
                </div>
                <h4 className="font-semibold text-sm mb-1">{m.title}</h4>
                <p className="text-xs text-muted-foreground leading-relaxed">{m.desc}</p>
              </div>
              {i < methodology.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-2.5 w-5 h-0.5 bg-border" />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
            <Database className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h3 className="font-semibold">About This Project</h3>
            <p className="text-xs text-muted-foreground">{"Fixture IQ — Sports Analytics Research"}</p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Fixture IQ is a data-driven research project that analyses the impact of fixture congestion 
          on Premier League clubs competing in European competitions. The project combines match scheduling data, 
          performance metrics, and squad rotation indicators to provide evidence-based insights for 
           football decision-makers. All data covers the {season} season and focuses on clubs participating
          in the Champions League, Europa League, and Conference League alongside their domestic commitments.
        </p>
      </div>
    </div>
  );
}
