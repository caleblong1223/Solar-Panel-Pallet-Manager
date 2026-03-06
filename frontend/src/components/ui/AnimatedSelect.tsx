import { useEffect, useId, useRef, useState } from "react";

export type AnimatedSelectOption = {
  value: string;
  label: string;
};

type AnimatedSelectProps = {
  label: string;
  value: string;
  placeholder?: string;
  options: AnimatedSelectOption[];
  onChange: (value: string) => void;
  variant?: "default" | "pill";
  className?: string;
};

const OPEN_EVENT = "pm:animated-select-open";

export default function AnimatedSelect({
  label,
  value,
  placeholder,
  options,
  onChange,
  variant = "default",
  className,
}: AnimatedSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const selectId = useId();
  const rootRef = useRef<HTMLLabelElement | null>(null);

  const currentLabel =
    options.find((opt) => opt.value === value)?.label ?? (value ? value : placeholder ?? "Select...");

  const handleSelect = (nextValue: string) => {
    onChange(nextValue);
    setIsOpen(false);
  };

  useEffect(() => {
    const onGlobalOpen = (event: Event) => {
      const customEvent = event as CustomEvent<{ id: string }>;
      if (customEvent.detail?.id !== selectId) {
        setIsOpen(false);
      }
    };
    window.addEventListener(OPEN_EVENT, onGlobalOpen);
    return () => {
      window.removeEventListener(OPEN_EVENT, onGlobalOpen);
    };
  }, [selectId]);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current) return;
      const target = event.target as Node | null;
      if (target && !rootRef.current.contains(target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  return (
    <label
      ref={rootRef}
      className={[
        "ui-input-label",
        "animated-select",
        variant === "pill" ? "animated-select--pill builder-active-pill builder-active-pill--input" : "",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <span>{label}</span>
      <button
        type="button"
        className="animated-select__control"
        onClick={() => {
          if (!isOpen) {
            window.dispatchEvent(new CustomEvent(OPEN_EVENT, { detail: { id: selectId } }));
          }
          setIsOpen((open) => !open);
        }}
      >
        <span className="animated-select__value">{currentLabel}</span>
        <span className="animated-select__caret">{isOpen ? "▲" : "▼"}</span>
      </button>
      <div
        className={
          isOpen
            ? "animated-select__options animated-select__options--open"
            : "animated-select__options"
        }
      >
        {options.map((opt) => (
          <button
            key={opt.value || opt.label}
            type="button"
            className="animated-select__option"
            onClick={() => handleSelect(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </label>
  );
}

