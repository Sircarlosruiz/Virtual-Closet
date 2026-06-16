"use client";

import { useRef, useState, useCallback, useEffect } from "react";

interface OtpInputProps {
  length?: number;
  onComplete: (code: string) => void;
  disabled?: boolean;
  error?: string;
  autoFocus?: boolean;
  autocomplete?: string;
}

export function OtpInput({
  length = 6,
  onComplete,
  disabled = false,
  error,
  autoFocus = false,
  autocomplete,
}: OtpInputProps) {
  const [values, setValues] = useState<string[]>(Array(length).fill(""));
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (autoFocus && inputsRef.current[0]) {
      inputsRef.current[0].focus();
    }
  }, [autoFocus]);

  const handleChange = useCallback(
    (index: number, char: string) => {
      if (disabled) return;

      // Only allow digits
      if (char && !/^\d$/.test(char)) return;

      const newValues = [...values];
      newValues[index] = char;
      setValues(newValues);

      // Auto-focus next input
      if (char && index < length - 1 && inputsRef.current[index + 1]) {
        inputsRef.current[index + 1]!.focus();
      }

      // Check if complete
      if (char && newValues.every((v) => v !== "")) {
        onComplete(newValues.join(""));
      }
    },
    [values, length, onComplete, disabled]
  );

  const handleKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (disabled) return;

      if (e.key === "Backspace") {
        e.preventDefault();
        const newValues = [...values];
        if (values[index]) {
          newValues[index] = "";
          setValues(newValues);
        } else if (index > 0 && inputsRef.current[index - 1]) {
          inputsRef.current[index - 1]!.focus();
          newValues[index - 1] = "";
          setValues(newValues);
        }
      } else if (e.key === "ArrowLeft" && index > 0) {
        inputsRef.current[index - 1]?.focus();
      } else if (e.key === "ArrowRight" && index < length - 1) {
        inputsRef.current[index + 1]?.focus();
      }
    },
    [values, length, disabled]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      if (disabled) return;

      const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
      if (!pasted) return;

      const newValues = [...values];
      for (let i = 0; i < pasted.length; i++) {
        newValues[i] = pasted[i];
      }
      setValues(newValues);

      // Focus the next empty input or the last one
      const nextIndex = Math.min(pasted.length, length - 1);
      inputsRef.current[nextIndex]?.focus();

      if (newValues.every((v) => v !== "")) {
        onComplete(newValues.join(""));
      }
    },
    [values, length, onComplete, disabled]
  );

  const inputClass = (index: number) =>
    `h-14 w-12 text-center text-2xl font-mono rounded-xl border-2 outline-none transition-all ` +
    `focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 ` +
    (error
      ? "border-red-400 bg-red-50"
      : values[index]
        ? "border-indigo-400 bg-indigo-50"
        : "border-gray-200 bg-white");

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex gap-2" onPaste={handlePaste}>
        {Array.from({ length }).map((_, index) => (
          <input
            key={index}
            ref={(el) => {
              inputsRef.current[index] = el;
            }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={values[index]}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            disabled={disabled}
            autoComplete={autocomplete}
            className={inputClass(index)}
            aria-label={`Dígito ${index + 1}`}
          />
        ))}
      </div>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
