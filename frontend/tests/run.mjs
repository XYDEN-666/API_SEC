/**
 * Test entry point.
 *
 * `node --test` runs each file in a spawned child process, which some
 * sandboxed/CI environments block. Importing the files into a single process
 * produces the same TAP output and works everywhere Node 18+ does, so
 * `npm test` uses this file.
 */

await import("./domain.test.mjs");
await import("./format.test.mjs");
