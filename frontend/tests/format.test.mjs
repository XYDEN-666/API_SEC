/** Unit tests for the date/number/text formatting helpers. */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  capitalize,
  formatDate,
  formatDateTime,
  formatDuration,
  formatNumber,
  formatRelative,
  initialsFromEmail,
  pluralize,
  truncateMiddle,
} from "../src/lib/format.js";

const NOW = new Date("2026-09-24T12:00:00Z");

test("formatDateTime and formatDate handle missing values", () => {
  assert.equal(formatDateTime(null), "—");
  assert.equal(formatDateTime(undefined), "—");
  assert.equal(formatDateTime("not-a-date"), "—");
  assert.equal(formatDate(null), "—");
  assert.notEqual(formatDateTime("2026-09-24T12:00:00Z"), "—");
});

test("formatRelative describes recent and older instants", () => {
  assert.equal(formatRelative(new Date(NOW.getTime() - 5_000), NOW), "just now");
  assert.equal(
    formatRelative(new Date(NOW.getTime() - 2 * 60_000), NOW),
    "2 minutes ago",
  );
  assert.equal(
    formatRelative(new Date(NOW.getTime() - 3 * 60 * 60_000), NOW),
    "3 hours ago",
  );
  assert.equal(
    formatRelative(new Date(NOW.getTime() - 2 * 24 * 60 * 60_000), NOW),
    "2 days ago",
  );
  assert.equal(formatRelative("2026-09-25T12:00:00Z", NOW), "tomorrow");
  assert.equal(formatRelative(null, NOW), "—");
});

test("formatDuration reports seconds, then minutes, and null without an end", () => {
  assert.equal(
    formatDuration("2026-09-24T12:00:00Z", "2026-09-24T12:00:01.5Z"),
    "1.5s",
  );
  assert.equal(
    formatDuration("2026-09-24T12:00:00Z", "2026-09-24T12:00:42Z"),
    "42s",
  );
  assert.equal(
    formatDuration("2026-09-24T12:00:00Z", "2026-09-24T12:02:07Z"),
    "2m 07s",
  );
  assert.equal(formatDuration("2026-09-24T12:00:00Z", null), null);
  assert.equal(formatDuration(null, null), null);
});

test("formatNumber and pluralize read naturally", () => {
  assert.equal(formatNumber(1234), "1,234");
  assert.equal(pluralize(1, "finding"), "1 finding");
  assert.equal(pluralize(0, "finding"), "0 findings");
  assert.equal(pluralize(2, "project"), "2 projects");
  assert.equal(pluralize(1, "identity", "identities"), "1 identity");
  assert.equal(pluralize(3, "identity", "identities"), "3 identities");
});

test("initialsFromEmail derives avatar text", () => {
  assert.equal(initialsFromEmail("ada@example.com"), "AD");
  assert.equal(initialsFromEmail("ada.lovelace@example.com"), "AL");
  assert.equal(initialsFromEmail("ada_lovelace@example.com"), "AL");
  assert.equal(initialsFromEmail("a@example.com"), "A");
  assert.equal(initialsFromEmail(""), "?");
  assert.equal(initialsFromEmail(null), "?");
});

test("truncateMiddle keeps both ends of long identifiers", () => {
  assert.equal(truncateMiddle("short-id"), "short-id");
  const long = "scan-1234567890-abcdefghij-0987654321-zyxwvutsrq";
  const result = truncateMiddle(long, 20);
  assert.ok(result.length <= 20, `expected <= 20, got ${result.length}`);
  assert.ok(result.includes("…"));
  assert.ok(result.startsWith("scan-1234"));
});

test("capitalize only touches the first character", () => {
  assert.equal(capitalize("completed"), "Completed");
  assert.equal(capitalize(""), "");
  assert.equal(capitalize(null), "");
});
