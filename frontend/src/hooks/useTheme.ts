import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "apishield.theme";

function readInitialTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark") {
      return stored;
    }
  } catch {
    // Storage can be unavailable (private mode); fall back to the OS setting.
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/** Theme preference, applied to <html data-theme> and remembered locally. */
export function useTheme(): { theme: Theme; setTheme: (value: Theme) => void } {
  const [theme, setThemeState] = useState<Theme>(readInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Preference simply won't persist.
    }
  }, [theme]);

  const setTheme = useCallback((value: Theme) => setThemeState(value), []);
  return { theme, setTheme };
}
