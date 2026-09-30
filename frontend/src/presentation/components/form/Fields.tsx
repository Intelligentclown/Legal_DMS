import { useId } from "react";
import type { ReactNode } from "react";

import {
  inputClassName,
  selectClassName,
  textareaClassName,
} from "@/presentation/components/form/styles";

interface FieldFrameProps {
  id: string;
  label: string;
  hint?: string;
  error?: string | null;
  children: (describedBy: string | undefined) => ReactNode;
}

function FieldFrame({ id, label, hint, error, children }: FieldFrameProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      {children(describedBy)}
      {hint ? (
        <p id={hintId} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="text-xs text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "email" | "tel" | "datetime-local";
  hint?: string;
  error?: string | null;
  disabled?: boolean;
  required?: boolean;
  maxLength?: number;
  placeholder?: string;
  name?: string;
}

export function TextField({
  label,
  value,
  onChange,
  type = "text",
  hint,
  error,
  disabled = false,
  required = false,
  maxLength,
  placeholder,
  name,
}: TextFieldProps) {
  const generatedId = useId();

  return (
    <FieldFrame id={generatedId} label={label} hint={hint} error={error}>
      {(describedBy) => (
        <input
          id={generatedId}
          name={name ?? generatedId}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          required={required}
          maxLength={maxLength}
          placeholder={placeholder}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={inputClassName}
        />
      )}
    </FieldFrame>
  );
}

export interface TextAreaFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  error?: string | null;
  disabled?: boolean;
  required?: boolean;
  maxLength?: number;
  placeholder?: string;
}

export function TextAreaField({
  label,
  value,
  onChange,
  hint,
  error,
  disabled = false,
  required = false,
  maxLength,
  placeholder,
}: TextAreaFieldProps) {
  const generatedId = useId();

  return (
    <FieldFrame id={generatedId} label={label} hint={hint} error={error}>
      {(describedBy) => (
        <textarea
          id={generatedId}
          name={generatedId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          required={required}
          maxLength={maxLength}
          placeholder={placeholder}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={textareaClassName}
        />
      )}
    </FieldFrame>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  hint?: string;
  error?: string | null;
  disabled?: boolean;
  required?: boolean;
  placeholder?: string;
}

/**
 * A `<select>` whose option values are opaque reference identifiers supplied by
 * the caller — the rendered labels are what the user reads and chooses by, so
 * no internal id is ever something a user has to type.
 */
export function SelectField({
  label,
  value,
  onChange,
  options,
  hint,
  error,
  disabled = false,
  required = false,
  placeholder = "Select…",
}: SelectFieldProps) {
  const generatedId = useId();

  return (
    <FieldFrame id={generatedId} label={label} hint={hint} error={error}>
      {(describedBy) => (
        <select
          id={generatedId}
          name={generatedId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={selectClassName}
        >
          <option value="">{placeholder}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </FieldFrame>
  );
}
