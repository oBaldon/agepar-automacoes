import { useTheme } from "../theme/ThemeProvider";
import { useState } from "react";

export default function ThemeToggle(){
  const { theme, setThemeChoice } = useTheme();
  const [open, setOpen] = useState(false);
  const order: Array<"light"|"dark"|"system"> = ["light","dark","system"];
  const next = () => {
    const i = order.indexOf(theme);
    setThemeChoice(order[(i+1) % order.length]);
  };
  return (
    <div className="theme-toggle">
      <button className="btn-ghost" title={`Tema: ${theme}`} onClick={() => setOpen(v => !v)}>
        🎨 {theme}
      </button>
      {open && (
        <div className="menu">
          <button onClick={() => setThemeChoice("light")}>Claro</button>
          <button onClick={() => setThemeChoice("dark")}>Escuro</button>
          <button onClick={() => setThemeChoice("system")}>Sistema</button>
        </div>
      )}
      <button className="btn-ghost small" title="Alternar rapidamente" onClick={next}>↻</button>
    </div>
  );
}
