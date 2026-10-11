import { useEffect, useState } from "react";
import Icon from "../Icon";

interface CopyButtonProps {
  value: string;
  label?: string;
}

/** Copies text to the clipboard and confirms it inline. */
export default function CopyButton({ value, label = "Copy" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const timer = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      // Clipboard access can be blocked; fall back to selecting the text.
      const area = document.createElement("textarea");
      area.value = value;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
      setCopied(true);
    }
  }

  return (
    <button type="button" className="copy-button" onClick={() => void handleCopy()}>
      <Icon name={copied ? "check" : "copy"} size={12} />
      {copied ? "Copied" : label}
    </button>
  );
}
