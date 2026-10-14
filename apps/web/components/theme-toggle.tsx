"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("timetable-theme");
    const enabled = saved === "dark";
    setDark(enabled);
    document.documentElement.dataset.theme = enabled ? "dark" : "light";
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.dataset.theme = next ? "dark" : "light";
    window.localStorage.setItem("timetable-theme", next ? "dark" : "light");
  }

  return (
    <button className="theme-toggle" type="button" onClick={toggle} aria-label={dark ? "Use light theme" : "Use dark theme"}>
      <span aria-hidden="true">{dark ? "☀" : "☾"}</span>
      <small>{dark ? "Light" : "Dark"}</small>
    </button>
  );
}
