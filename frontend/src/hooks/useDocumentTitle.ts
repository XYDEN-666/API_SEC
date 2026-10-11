import { useEffect } from "react";

/** Set the document title, restoring the base title on unmount. */
export function useDocumentTitle(title?: string): void {
  useEffect(() => {
    const previous = document.title;
    if (title !== undefined) {
      document.title = `${title} · APIShield`;
    }
    return () => {
      document.title = previous;
    };
  }, [title]);
}
