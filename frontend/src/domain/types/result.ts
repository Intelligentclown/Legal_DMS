/**
 * Result<T, E>: an explicit success/failure type for operations whose
 * failure is an expected, handleable outcome — not a thrown exception.
 * Mirrors the backend's `Result[T, E]` (see
 * `backend/src/app/domain/common/result.py`), adapted to a TS discriminated
 * union rather than a class, since that's the idiomatic pattern here.
 */
export type Result<T, E = string> = { success: true; value: T } | { success: false; error: E };

export function ok<T, E = string>(value: T): Result<T, E> {
  return { success: true, value };
}

export function err<T, E = string>(error: E): Result<T, E> {
  return { success: false, error };
}

export function isOk<T, E>(result: Result<T, E>): result is { success: true; value: T } {
  return result.success;
}

export function isErr<T, E>(result: Result<T, E>): result is { success: false; error: E } {
  return !result.success;
}
