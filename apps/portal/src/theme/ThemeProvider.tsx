import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { ThemePref, getStoredPref, setPref, applyTheme, systemPrefersDark } from "./theme";

type Ctx = {
  pref: ThemePref;                       // null = seguir sistema
  setPrefChoice: (p: ThemePref) => void; // define explicitamente
};
const C = createContext<Ctx>({ pref: null, setPrefChoice: () => {} });
export const useTheme = () => useContext(C);

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [pref, setPrefState] = useState<ThemePref>(() => getStoredPref());

  useEffect(() => {
    applyTheme(pref);
    if (pref !== null) return; // só observa o sistema quando seguimos o sistema
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme(null);
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, [pref]);

  const api = useMemo<Ctx>(() => ({
    pref,
    setPrefChoice: (p) => { setPrefState(p); setPref(p); }
  }), [pref]);

  return <C.Provider value={api}>{children}</C.Provider>;
}
