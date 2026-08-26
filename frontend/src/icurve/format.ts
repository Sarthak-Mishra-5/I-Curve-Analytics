// Strip the leading product prefix for compact display, e.g.
// "SR3 Sep26" -> "Sep26", "I Sep26 3MF" -> "Sep26 3MF".
export function shortTenor(name: string): string {
  return name.replace(/^[A-Z0-9]+\s+/, '');
}

// "I" is the legacy Euribor curve id and keeps its historical "ER" leg
// prefix; every other curve derives its prefix from its own curve_id (e.g.
// "SR3" -> "SR", "SA3" -> "SA") so new curves get correct labels for free.
function legPrefix(curveId: string): string {
  if (curveId === 'I') return 'ER';
  return curveId.replace(/\d+$/, '') || curveId;
}

// Rolling front-relative label for an outright, e.g. outrights[0] -> "ER1"/
// "SR1"/etc. (current front month), outrights[1] -> "…2", etc. — the label
// stays meaningful as contracts expire and the front month advances, unlike
// a fixed calendar tenor. Falls back to the tenor itself if `name` isn't one
// of the given outrights.
export function erLabel(outrights: string[], name: string, curveId = 'I'): string {
  const idx = outrights.indexOf(name);
  return idx >= 0 ? `${legPrefix(curveId)}${idx + 1}` : shortTenor(name);
}

// Correlation-strength threshold coloring shared across correlation tables.
// (StructureBuilder.tsx and CurveStatsTable.tsx each still carry their own
// private copy of this — safe to leave as-is; new code should import this one.)
export function corrColor(c: number | null): string {
  if (c == null) return '#666666';
  const a = Math.abs(c);
  if (a >= 0.7) return '#00ff88';
  if (a >= 0.4) return '#ffaa00';
  return '#e5e5e5';
}
