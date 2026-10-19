export const field =
  "mt-1.5 min-h-11 w-full rounded-xl border border-rule bg-field px-3 text-base text-ink shadow-sm outline-none transition placeholder:text-muted/70 focus:border-seal"

export const primary =
  "inline-flex min-h-11 items-center justify-center rounded-xl bg-seal px-4 text-sm font-semibold text-seal-ink shadow-sm transition hover:opacity-90 active:opacity-80 disabled:cursor-not-allowed disabled:bg-rule disabled:text-muted"

export const secondary =
  "inline-flex min-h-11 items-center justify-center rounded-xl border border-rule bg-field px-3 text-sm font-medium text-ink transition hover:border-seal/40 disabled:opacity-60"

export const card =
  "rounded-2xl border border-rule bg-field p-5 shadow-[0_1px_2px_rgba(26,24,20,0.04),0_18px_40px_rgba(26,24,20,0.05)]"

export function chip(on: boolean): string {
  return `inline-flex min-h-11 items-center rounded-full px-3.5 text-sm font-medium transition ${
    on ? "bg-ink text-paper" : "border border-rule bg-field text-ink hover:border-seal/40"
  }`
}
