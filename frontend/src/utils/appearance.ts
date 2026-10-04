export type Theme = "light" | "dark";

export const FONT_SCALE_MIN = 80;
export const FONT_SCALE_MAX = 140;
export const FONT_SCALE_DEFAULT = 100;

const THEME_KEY = "navee.theme";
const FONT_KEY = "navee.fontScale";

export function getStoredTheme(): Theme | null {
  const v = localStorage.getItem(THEME_KEY);
  return v === "light" || v === "dark" ? v : null;
}

export function getSystemTheme(): Theme {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function getInitialTheme(): Theme {
  return getStoredTheme() ?? getSystemTheme();
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function getStoredFontScale(): number {
  const n = parseInt(localStorage.getItem(FONT_KEY) ?? "", 10);
  if (Number.isNaN(n)) return FONT_SCALE_DEFAULT;
  return Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, n));
}

export function applyFontScale(pct: number): void {
  document.documentElement.style.fontSize = `${pct}%`;
}

/**
 * Re-applies the system theme when the OS preference changes and the user
 * has no stored choice. Returns an unsubscribe function.
 */
export function followSystemTheme(): () => void {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const onChange = () => {
    if (!getStoredTheme()) applyTheme(getSystemTheme());
  };
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}
