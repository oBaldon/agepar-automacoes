export type ThemeChoice = "light" | "dark" | "system";
const STORAGE_KEY = "theme";

export function getStoredTheme(): ThemeChoice {
  return (localStorage.getItem(STORAGE_KEY) as ThemeChoice) || "system";
}
export function getSystemPrefersDark(): boolean {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}
export function applyTheme(choice: ThemeChoice) {
  const html = document.documentElement;
  const dark = choice === "dark" || (choice === "system" && getSystemPrefersDark());
  if (dark) html.setAttribute("data-theme","dark"); else html.removeAttribute("data-theme");
}
export function setTheme(choice: ThemeChoice) {
  localStorage.setItem(STORAGE_KEY, choice);
  applyTheme(choice);
}
