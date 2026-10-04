export type Theme = "light" | "dark";
export type FontScale = "sm" | "md" | "lg" | "xl";

export const FONT_SCALE_DEFAULT: FontScale = "md";

export const FONT_SCALES: { id: FontScale; label: string; value: number }[] = [
  { id: "sm", label: "Small", value: 0.875 },
  { id: "md", label: "Medium", value: 1 },
  { id: "lg", label: "Large", value: 1.125 },
  { id: "xl", label: "X-Large", value: 1.25 },
];

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

export function getStoredFontScale(): FontScale {
  const v = localStorage.getItem(FONT_KEY);
  if (v === "sm" || v === "md" || v === "lg" || v === "xl") return v;
  return FONT_SCALE_DEFAULT;
}

export function applyFontScale(scale: FontScale): void {
  const entry = FONT_SCALES.find((f) => f.id === scale);
  if (entry) document.documentElement.style.setProperty("--font-scale", String(entry.value));
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
