export type ThemePref = "light" | "dark" | null; // null = seguir sistema
const KEY = "themePref";

export function getStoredPref(): ThemePref {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : null;
}
export function systemPrefersDark(): boolean {
  return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
}
export function effectiveTheme(pref: ThemePref): "light" | "dark" {
  return pref === null ? (systemPrefersDark() ? "dark" : "light") : pref;
}
export function applyTheme(pref: ThemePref) {
  const dark = effectiveTheme(pref) === "dark";
  const html = document.documentElement;
  dark ? html.setAttribute("data-theme","dark") : html.removeAttribute("data-theme");
}
export function setPref(pref: ThemePref) {
  if (pref) localStorage.setItem(KEY, pref);
  else localStorage.removeItem(KEY);
  applyTheme(pref);
}
export function invertPref(pref: ThemePref): ThemePref {
  // inverte o tema efetivo; deixa armazenado como explícito (light/dark)
  const cur = effectiveTheme(pref);
  return cur === "dark" ? "light" : "dark";
}
