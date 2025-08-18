import { useMemo } from "react";
import { useTheme } from "../theme/ThemeProvider";
import { effectiveTheme, invertPref } from "../theme/theme";

export default function ThemeToggle(){
  const { pref, setPrefChoice } = useTheme();

  const icon = useMemo(() => {
    return effectiveTheme(pref) === "dark" ? "☀️" : "🌙";
  }, [pref]);

  const title = useMemo(() => {
    return effectiveTheme(pref) === "dark" ? "Trocar para claro" : "Trocar para escuro";
  }, [pref]);

  function onClick(){
    setPrefChoice(invertPref(pref)); // passa a guardar explícito (light/dark)
  }

  return (
    <button className="btn-icon theme-toggle-alone" onClick={onClick} title={title} aria-label={title}>
      {icon}
    </button>
  );
}
