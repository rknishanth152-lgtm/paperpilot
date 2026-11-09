// The PaperPilot mark: lines of text that form a heading, the highlighted line
// leading. The same drawing is public/favicon.svg.

export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg viewBox="0 0 256 256" width={size} height={size} aria-hidden="true" focusable="false">
      <rect width="256" height="256" rx="56" fill="#0E5A5E" />
      <g transform="translate(38.4 38.4) scale(.7)">
        <path fill="#fff" d="M36 48H140L164 92H60Z" />
        <path fill="#FFE36E" d="M28 106H194L228 128L194 150H28Z" />
        <path fill="#fff" d="M60 164H164L140 208H36Z" />
      </g>
    </svg>
  );
}
