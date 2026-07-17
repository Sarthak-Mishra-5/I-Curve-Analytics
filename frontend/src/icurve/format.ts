// Strip the leading "I " product prefix for compact display, e.g.
// "I Sep26" -> "Sep26", "I Sep26 3MF" -> "Sep26 3MF".
export function shortTenor(name: string): string {
  return name.replace(/^I\s+/, '');
}

// Rolling front-relative label for an outright, e.g. outrights[0] -> "ER1"
// (current front month), outrights[1] -> "ER2", etc. — the label stays
// meaningful as contracts expire and the front month advances, unlike a
// fixed calendar tenor. Falls back to the tenor itself if `name` isn't one
// of the given outrights.
export function erLabel(outrights: string[], name: string): string {
  const idx = outrights.indexOf(name);
  return idx >= 0 ? `ER${idx + 1}` : shortTenor(name);
}
