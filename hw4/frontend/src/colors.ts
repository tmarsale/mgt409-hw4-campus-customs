// Swatch colors for the color names used in the catalogue ("navy blue", "heather gray", ...).
// Used only to draw small color dots next to the real color names; the names come from the database.

const SWATCHES: [RegExp, string][] = [
  [/charcoal|dark heather/, "#4b4f58"],
  [/navy/, "#1c2b4f"],
  [/royal|light blue|sky/, "#5b8fd1"],
  [/blue/, "#2d5aa6"],
  [/heather|gray|grey|silver/, "#a5a8ad"],
  [/white|ivory/, "#ffffff"],
  [/cream|natural|oat|sand|tan|khaki|beige/, "#e9dfc8"],
  [/black/, "#151515"],
  [/maroon|burgundy|crimson/, "#7a1f2b"],
  [/red/, "#b8282f"],
  [/pink/, "#e6a1b6"],
  [/orange/, "#e07b2e"],
  [/yellow|gold/, "#e2b93b"],
  [/green/, "#2f6b47"],
  [/purple|violet/, "#5d3f8e"],
  [/brown/, "#6b4a32"],
];

export function swatch(colorName: string): string {
  const name = colorName.toLowerCase();
  return SWATCHES.find(([pattern]) => pattern.test(name))?.[1] ?? "#c9c4b8";
}
