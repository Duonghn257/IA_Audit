import { describe, expect, it } from "vitest"

import { formatBytes, formatRelativeTime } from "../../src/shared/formatting/date"

describe("formatting helpers", () => {
  it("formats file sizes", () => {
    expect(formatBytes(512)).toBe("512 B")
    expect(formatBytes(1536)).toBe("1.5 KB")
    expect(formatBytes(2 * 1024 * 1024)).toBe("2.0 MB")
  })

  it("formats relative timestamps", () => {
    expect(
      formatRelativeTime("2026-07-29T09:59:00Z", new Date("2026-07-29T10:00:00Z")),
    ).toBe("1 minute ago")
  })
})
