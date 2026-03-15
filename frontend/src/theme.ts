// src/theme.ts
// Design tokens matching mockup exactly.
// Use these in inline styles for dynamic values (experience colors).
// CSS Modules reference the hex values directly for static uses.

export const colors = {
  bgApp: '#1e1208',
  bgTopbar: '#120c05',
  bgSidebar: '#0e0905',
  bgCard: '#201408',
  bgCardDetail: '#180e06',
  bgCardHover: '#281a0a',
  borderDefault: '#2a1810',
  borderCard: '#362010',
  accentGold: '#e8c070',
  accentGoldHover: '#f0cc7c',
  textBody: '#f0ddb8',
  textMuted1: '#5a3e22',   // dim labels
  textMuted2: '#6a5038',   // secondary text
  textMuted3: '#8a7058',   // description text
  textDim: '#3e2810',      // very dim / disabled
} as const

// Fixed palette cycled by experience id
export const experiencePalette: string[] = [
  '#c4782a',  // orange
  '#6880c8',  // blue
  '#50a8c0',  // teal
  '#72a848',  // green
  '#a068c8',  // purple
  '#c87870',  // rose
  '#78a890',  // sea green
  '#c8b840',  // yellow
]

export function getExperienceColor(id: number): string {
  return experiencePalette[id % experiencePalette.length]
}
