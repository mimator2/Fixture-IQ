import TeamGrid from "../components/TeamGrid";

export default function Teams() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Teams Overview</h1>
        <p className="text-muted-foreground">
          Premier League clubs analysed for fixture congestion impact during the 2023-24 season
        </p>
      </div>
      <TeamGrid />
    </div>
  );
}