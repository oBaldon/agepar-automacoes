import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { ThemeChoice, getStoredTheme, setTheme, applyTheme } from "./theme";

type Ctx = { theme: ThemeChoice; setThemeChoice: (t: ThemeChoice) => void; };
const ThemeCtx = createContext<Ctx>({ theme: "system", setThemeChoice: () => {} });
export function useTheme(){ return useContext(ThemeCtx); }

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeChoice>(() => getStoredTheme());
  useEffect(() => {
    applyTheme(theme);
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, [theme]);

  const api = useMemo<Ctx>(() => ({
    theme,
    setThemeChoice: (t) => { setThemeState(t); setTheme(t); }
  }), [theme]);

  return <ThemeCtx.Provider value={api}>{children}</ThemeCtx.Provider>;
}
