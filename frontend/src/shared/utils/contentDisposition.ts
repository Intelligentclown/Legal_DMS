/**
 * Reads the filename out of a `Content-Disposition` response header.
 *
 * The backend's download route builds `attachment; filename="<X-Filename>"` by
 * interpolating the stored filename without encoding it, so the value is also
 * sanitized before it is reused as a local download name.
 */

const QUOTED_FILENAME = /filename\s*=\s*"([^"]*)"/i;
const BARE_FILENAME = /filename\s*=\s*([^;]+)/i;

function isPrintable(character: string): boolean {
  const code = character.codePointAt(0) ?? 0;
  return code >= 0x20 && code !== 0x7f;
}

/** Drops control characters, then quotes and path separators, then trims. */
export function sanitizeFilename(value: string): string {
  return Array.from(value)
    .filter(isPrintable)
    .join("")
    .replace(/[/\\"]/g, "_")
    .trim();
}

export function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) {
    return null;
  }

  const quoted = QUOTED_FILENAME.exec(header);
  const raw = quoted ? quoted[1] : (BARE_FILENAME.exec(header)?.[1] ?? "");
  const sanitized = sanitizeFilename(raw);

  return sanitized ? sanitized : null;
}
