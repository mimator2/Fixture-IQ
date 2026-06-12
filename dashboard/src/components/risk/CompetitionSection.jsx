import { Trophy } from "lucide-react";
import InfoTip, { METRIC_HELP } from "@/components/ui/InfoTip";

const Row = ({ label, value, highlight, help }) => (
  <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
    <span className="text-sm text-muted-foreground flex items-center">
      {label}
      {help && <InfoTip text={help} />}
    </span>
    <span className={`text-sm font-semibold ${highlight ? "text-chart-5" : "text-foreground"}`}>{value ?? "—"}</span>
  </div>
);

export default function CompetitionSection({ player }) {
  const shortRestAfterUCL = (player.days_since_last_european != null && player.days_since_last_european <= 4 && (player.ucl_minutes_last_21 ?? 0) > 0) ? "Yes" : "No";
  const compSwitches = (() => {
    let count = 0;
    if ((player.ucl_minutes_last_21 ?? 0) > 0) count += 1;
    if ((player.cup_minutes_last_14 ?? 0) > 0) count += 1;
    return count;
  })();

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <Trophy className="w-4 h-4 text-primary" />
        <h3 className="font-semibold">Multi-Competition</h3>
      </div>
      <div>
        <Row label="UCL minutes (21d)"        value={player.ucl_minutes_last_21}                              highlight={(player.ucl_minutes_last_21 ?? 0) >= 90} />
        <Row label="UCL matches (30d)"        value={player.ucl_matches_last_30}                              highlight={(player.ucl_matches_last_30 ?? 0) >= 2} />
        <Row label="Cup minutes (14d)"        value={player.cup_minutes_last_14}                              highlight={(player.cup_minutes_last_14 ?? 0) >= 90} />
        <Row label="Cup matches (30d)"        value={player.cup_matches_last_30}                              highlight={(player.cup_matches_last_30 ?? 0) >= 2} />
        <Row label="PL after UCL short rest"  value={shortRestAfterUCL}                                       highlight={shortRestAfterUCL === "Yes"} />
        <Row label="Days since European"      value={player.days_since_last_european != null ? `${player.days_since_last_european}d` : null} highlight={(player.days_since_last_european ?? 99) <= 4} />
        <Row label="Comp switches (21d)"      value={compSwitches}                                            highlight={compSwitches >= 2} help={METRIC_HELP.competition_switches} />
      </div>
    </div>
  );
}