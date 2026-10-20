/** Small line icons for the shell and the home page. */

export type IconName =
  | "menu"
  | "globe"
  | "briefcase"
  | "upload"
  | "bell"
  | "ext"
  | "pdf"
  | "doc"
  | "share"
  | "up"
  | "down"
  | "lock"
  | "refresh"
  | "wifiOff"
  | "copy"
  | "info"
  | "arrow"
  | "alert"
  | "compass"
  | "map"
  | "ban"
  | "listck"
  | "plus"
  | "home"
  | "chat"
  | "calculator"
  | "filer"
  | "notice"
  | "checklist"
  | "updates"
  | "experts"
  | "evaluation"
  | "privacy"
  | "clear"
  | "collapse"
  | "expand"
  | "panelLeft"
  | "panelRight"
  | "sun"
  | "moon"
  | "filing"
  | "search"
  | "pencil"
  | "link"
  | "trash"
  | "check"
  | "close"
  | "user"
  | "gear"
  | "dots"
  | "chev"
  | "checkShield"
  | "calc"

const PATHS: Record<IconName, string> = {
  globe: "M3.5 12a8.5 8.5 0 1 0 17 0a8.5 8.5 0 1 0-17 0M3.5 12h17M12 3.5c2.5 2.6 2.5 14.4 0 17M12 3.5c-2.5 2.6-2.5 14.4 0 17",
  refresh: "M19 12a7 7 0 1 1-2.1-5M19 4.5V9h-4.5",
  wifiOff: "M4 4l16 16M8.5 16.5a5 5 0 0 1 7 0M5 13a10 10 0 0 1 5-2.7M14.5 10.4A10 10 0 0 1 19 13M2.5 9.5a14 14 0 0 1 4-2.6M11 6.1a14 14 0 0 1 10.5 3.4M12 19.4v.2",
  copy: "M10 8h7a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-7a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2zM5 15V6a1 1 0 0 1 1-1h9",
  info: "M3.5 12a8.5 8.5 0 1 0 17 0a8.5 8.5 0 1 0-17 0M12 11v5M12 8h.01",
  arrow: "M5 12h14M13 6l6 6-6 6",
  alert: "M12 4 2.5 20h19zM12 10v4M12 17h.01",
  compass: "M4 12a8 8 0 1 0 16 0a8 8 0 1 0-16 0M15 9l-2 5-4 1 2-5z",
  map: "M9 4 3 6v14l6-2 6 2 6-2V4l-6 2zM9 4v14M15 6v14",
  ban: "M4 12a8 8 0 1 0 16 0a8 8 0 1 0-16 0M6.5 6.5l11 11",
  listck: "M9 6h11M9 12h11M9 18h11M3.5 6l1.2 1.2L7 4.8M3.5 12l1.2 1.2L7 10.8M3.5 18l1.2 1.2L7 16.8",
  menu: "M4 7h16M4 12h16M4 17h16",
  plus: "M12 5v14M5 12h14",
  home: "M4 11.2 12 4.5l8 6.7V19.5H15v-5.2H9v5.2H4z",
  chat: "M5 6.5h14v9H8.5L5 18.5z",
  calculator: "M7 4.5h10v15H7zM9 8h6M9 12h.01M12 12h.01M15 12h.01M9 15h.01M12 15h.01M15 15h.01",
  filer: "M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6.5 19.5a5.5 5.5 0 0 1 11 0",
  notice: "M7 4.5h7l4 4V19.5H7zM14 4.5V9h4.5",
  checklist: "M8 7.5h10M8 12h10M8 16.5h10M4.5 7.5h.01M4.5 12h.01M4.5 16.5h.01",
  updates: "M5 6.5h14v11H5zM5 10.5h14M9 6.5v11",
  experts: "M8 11a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM16.5 11.5a2.2 2.2 0 1 0 0-4.4 2.2 2.2 0 0 0 0 4.4zM4.5 18.5a3.5 3.5 0 0 1 7 0M12.2 18.5a3.2 3.2 0 0 1 6.3-.8",
  evaluation: "M5 16.5l4.5-4.5 3 3 6.5-7",
  privacy: "M12 4.5l7 2.5v5.2c0 3.6-2.6 6.2-7 7.8-4.4-1.6-7-4.2-7-7.8V7z",
  clear: "M5 7.5h14M9.5 7.5V5.8h5V7.5M7.2 7.5l.7 11h8.2l.7-11",
  collapse: "M14.5 7.5 10 12l4.5 4.5M6 5.5v13",
  expand: "M9.5 7.5 14 12l-4.5 4.5M18 5.5v13",
  panelLeft: "M4.5 5h15v14h-15zM9.5 5v14",
  panelRight: "M4.5 5h15v14h-15zM14.5 5v14",
  sun: "M12 8.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6zM12 4.2v1.6M12 18.2v1.6M4.2 12H5.8M18.2 12h1.6M6.5 6.5l1.1 1.1M16.4 16.4l1.1 1.1M17.5 6.5l-1.1 1.1M7.6 16.4l-1.1 1.1",
  moon: "M15.2 5.2a6.4 6.4 0 1 0 3.2 11.4A5.4 5.4 0 0 1 15.2 5.2z",
  filing: "M7 4.5h6.5L17 8v11.5H7zM13.2 4.8V8H17M8.5 12h7M8.5 15.5h7",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM16.5 16.5 20 20",
  pencil: "M4 20h4L18.5 9.5l-4-4L4 16zM13.5 6.5l4 4",
  link: "M10 13.2a4.2 4.2 0 0 0 6 .1l1.2-1.2a4.2 4.2 0 0 0-6-6l-.7.7M14 10.8a4.2 4.2 0 0 0-6-.1l-1.2 1.2a4.2 4.2 0 0 0 6 6l.7-.7",
  trash: "M5 7.5h14M9.5 7.5V5.8h5V7.5M7.2 7.5l.7 11h8.2l.7-11",
  check: "M5 12.5 10 17.5 19 7.5",
  pdf: "M7 3.5h7l4 4v13H7zM14 3.5v4h4M9.5 16.5v-4h1.2a1.2 1.2 0 0 1 0 2.4H9.5",
  doc: "M6 5.5h7.2L17 9.2V18.5H6v-13zM13 5.5V9h4",
  share: "M12 4v11M8 8l4-4 4 4M5 13v5.5h14V13",
  up: "M7 11v8H4v-8zM7 11l4-7c1.5 0 2.5 1 2.2 2.5L12.8 10H18a2 2 0 0 1 2 2.3l-1 5.4A2 2 0 0 1 17 19H7",
  down: "M7 13V5H4v8zM7 13l4 7c1.5 0 2.5-1 2.2-2.5L12.8 14H18a2 2 0 0 0 2-2.3l-1-5.4A2 2 0 0 0 17 5H7",
  lock: "M6.5 11h11v8.5h-11zM8.5 11V8a3.5 3.5 0 0 1 7 0v3",
  briefcase: "M5 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM9 7V5h6v2",
  upload: "M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3",
  bell: "M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15zM10 20a2 2 0 0 0 4 0",
  ext: "M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5",
  close: "M7 7l10 10M17 7 7 17",
  user: "M8.5 8.5a3.5 3.5 0 1 0 7 0 3.5 3.5 0 1 0-7 0M5 20c1.2-3.6 4-5.5 7-5.5s5.8 1.9 7 5.5",
  gear: "M9 12a3 3 0 1 0 6 0 3 3 0 1 0-6 0M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7",
  dots: "M5 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0M11 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0M17 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0",
  chev: "m9 6 6 6-6 6",
  checkShield: "M12 3.5 5 6v5.5c0 4.2 2.9 7.6 7 9 4.1-1.4 7-4.8 7-9V6zM9 12l2.2 2.2L15.5 10",
  calc: "M8.5 3.5h7a2.5 2.5 0 0 1 2.5 2.5v12a2.5 2.5 0 0 1-2.5 2.5h-7A2.5 2.5 0 0 1 6 18V6a2.5 2.5 0 0 1 2.5-2.5zM9 7.5h6M9 12h.01M12 12h.01M15 12h.01M9 15.5h.01M12 15.5h.01M15 15.5h.01",
}

export default function Icon({ name, size = "md", className = "" }: { name: IconName; size?: "sm" | "md"; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`${size === "sm" ? "h-4 w-4" : "h-5 w-5"} shrink-0 ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={size === "sm" ? "1.7" : "1.5"}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
