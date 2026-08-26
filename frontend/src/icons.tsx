import type { SVGProps } from 'react'

type IconName = 'spark' | 'workflow' | 'book' | 'chart' | 'pulse' | 'search' | 'bell' | 'send' | 'plus' | 'chevron' | 'check' | 'clock' | 'quote' | 'thumbUp' | 'thumbDown' | 'copy' | 'more' | 'database' | 'upload' | 'file' | 'refresh' | 'play' | 'filter' | 'arrowUp' | 'menu' | 'close' | 'target' | 'shield' | 'message' | 'layers' | 'sun' | 'moon'

const paths: Record<IconName, JSX.Element> = {
  spark: <><path d="m12 3-1.4 4.3a3 3 0 0 1-1.9 1.9L4.5 10.5l4.2 1.3a3 3 0 0 1 1.9 1.9L12 18l1.4-4.3a3 3 0 0 1 1.9-1.9l4.2-1.3-4.2-1.3a3 3 0 0 1-1.9-1.9L12 3Z"/><path d="m5 3 .5 1.5L7 5l-1.5.5L5 7l-.5-1.5L3 5l1.5-.5L5 3Z"/></>,
  workflow: <><rect x="3" y="3" width="6" height="6" rx="1.5"/><rect x="15" y="15" width="6" height="6" rx="1.5"/><path d="M9 6h4a4 4 0 0 1 4 4v5M6 9v5a4 4 0 0 0 4 4h5"/></>,
  book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v17H6.5A2.5 2.5 0 0 0 4 22.5v-17Z"/><path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v17h4.5a2.5 2.5 0 0 1 2.5 2.5v-17Z"/></>,
  chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></>,
  pulse: <><path d="M3 12h4l2.2-6 4.2 12 2.4-6H21"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
  send: <><path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/></>,
  plus: <><path d="M12 5v14M5 12h14"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>,
  check: <path d="m5 12 4 4L19 6"/>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  quote: <><path d="M9 11H5a4 4 0 0 0 4 4V8a5 5 0 0 0-5 5"/><path d="M20 11h-4a4 4 0 0 0 4 4V8a5 5 0 0 0-5 5"/></>,
  thumbUp: <><path d="M7 10v10H3V10h4ZM7 18c4 2 10 2 11 0l2-6c.5-1.5-.5-3-2-3h-5l1-4c0-2-3-2-4 0l-3 5"/></>,
  thumbDown: <><path d="M7 14V4H3v10h4ZM7 6c4-2 10-2 11 0l2 6c.5 1.5-.5 3-2 3h-5l1 4c0 2-3 2-4 0l-3-5"/></>,
  copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>,
  more: <><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></>,
  database: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></>,
  upload: <><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/></>,
  file: <><path d="M6 2h8l5 5v15H6V2Z"/><path d="M14 2v6h5M9 13h6M9 17h6"/></>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6l-2 2M5.5 15A7 7 0 0 0 18 18l2-2"/></>,
  play: <path d="m8 5 11 7-11 7V5Z"/>,
  filter: <path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z"/>,
  arrowUp: <><path d="M12 19V5M6 11l6-6 6 6"/></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
  close: <><path d="m6 6 12 12M18 6 6 18"/></>,
  target: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 2v3M22 12h-3M12 22v-3M2 12h3"/></>,
  shield: <><path d="M12 2 4 5v6c0 5 3.4 9.3 8 11 4.6-1.7 8-6 8-11V5l-8-3Z"/><path d="m9 12 2 2 4-5"/></>,
  message: <><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z"/><path d="M8 9h8M8 13h5"/></>,
  layers: <><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/></>,
  sun: <><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42"/></>,
  moon: <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79Z"/>,
}

export function Icon({ name, size = 18, ...props }: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>
}
