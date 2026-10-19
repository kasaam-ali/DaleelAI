/** Small line icons for the shell and the home page. */

export type IconName =
  | "menu"
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

const PATHS: Record<IconName, string> = {
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
  close: "M7 7l10 10M17 7 7 17",
}

export default function Icon({ name }: { name: IconName }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
