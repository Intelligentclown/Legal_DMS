import { describe, expect, it } from "vitest";

import {
  parseContentDispositionFilename,
  sanitizeFilename,
} from "@/shared/utils/contentDisposition";

const BEL = String.fromCharCode(0x07);
const NUL = String.fromCharCode(0x00);
const DEL = String.fromCharCode(0x7f);

/**
 * The backend builds its download header by interpolating the filename stored
 * at upload, so parsing has to cope with whatever the client sent rather than
 * assuming a well-formed value.
 */
describe("parseContentDispositionFilename", () => {
  it("reads a quoted filename", () => {
    expect(parseContentDispositionFilename('attachment; filename="deed.pdf"')).toBe("deed.pdf");
  });

  it("reads a bare filename", () => {
    expect(parseContentDispositionFilename("attachment; filename=deed.pdf")).toBe("deed.pdf");
  });

  it("is case-insensitive about the header parameter name", () => {
    expect(parseContentDispositionFilename('attachment; FileName="deed.pdf"')).toBe("deed.pdf");
  });

  it("preserves spaces inside a quoted filename", () => {
    expect(
      parseContentDispositionFilename('attachment; filename="Board Minutes - March.pdf"'),
    ).toBe("Board Minutes - March.pdf");
  });

  it("returns null when the header is absent", () => {
    expect(parseContentDispositionFilename(null)).toBeNull();
  });

  it("returns null when the header carries no filename", () => {
    expect(parseContentDispositionFilename("attachment")).toBeNull();
  });

  it("returns null when the filename is only whitespace", () => {
    expect(parseContentDispositionFilename('attachment; filename="   "')).toBeNull();
  });

  it("still returns a name when the stored filename carried separators", () => {
    expect(parseContentDispositionFilename('attachment; filename="a/b.pdf"')).toBe("a_b.pdf");
  });
});

describe("sanitizeFilename", () => {
  it("replaces path separators so the name cannot escape a download folder", () => {
    expect(sanitizeFilename("../../etc/passwd")).toBe(".._.._etc_passwd");
    expect(sanitizeFilename("dir\\file.pdf")).toBe("dir_file.pdf");
  });

  it("replaces a quote so it cannot break out of the header", () => {
    expect(sanitizeFilename('a".pdf')).toBe("a_.pdf");
  });

  it("drops control characters", () => {
    expect(sanitizeFilename(`deed${BEL}.pdf`)).toBe("deed.pdf");
    expect(sanitizeFilename(`de${NUL}ed.pdf`)).toBe("deed.pdf");
    expect(sanitizeFilename(`deed${DEL}.pdf`)).toBe("deed.pdf");
  });

  it("keeps non-ASCII letters intact", () => {
    expect(sanitizeFilename("nota-española.pdf")).toBe("nota-española.pdf");
  });

  it("trims surrounding whitespace", () => {
    expect(sanitizeFilename("  deed.pdf  ")).toBe("deed.pdf");
  });
});
