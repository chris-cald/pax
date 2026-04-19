---
name: vitest
description: Vitest fast unit testing framework powered by Vite with Jest-compatible API. Use when writing tests, mocking, configuring coverage, or working with test filtering and fixtures.
metadata:
  author: Anthony Fu
  version: "2026.1.28"
  source: Generated from https://github.com/vitest-dev/vitest, scripts located at https://github.com/antfu/skills
---

# Vitest

Vitest is a next-generation testing framework powered by Vite. It provides a Jest-compatible API with native ESM, TypeScript, and JSX support out of the box. Vitest shares the same config, transformers, resolvers, and plugins with your Vite app.

**Key Features:**

- Vite-native: Uses Vite's transformation pipeline for fast HMR-like test updates
- Jest-compatible: Drop-in replacement for most Jest test suites
- Smart watch mode: Only reruns affected tests based on module graph
- Native ESM, TypeScript, JSX support without configuration
- Multi-threaded workers for parallel test execution
- Built-in coverage via V8 or Istanbul
- Snapshot testing, mocking, and spy utilities

> The skill is based on Vitest 3.x, generated at 2026-01-28.

## Core

| Topic         | Description                                                     | Reference                                    |
| ------------- | --------------------------------------------------------------- | -------------------------------------------- |
| Configuration | Vitest and Vite config integration, defineConfig usage          | [core-config](references/core-config.md)     |
| CLI           | Command line interface, commands and options                    | [core-cli](references/core-cli.md)           |
| Test API      | test/it function, modifiers like skip, only, concurrent         | [core-test-api](references/core-test-api.md) |
| Describe API  | describe/suite for grouping tests and nested suites             | [core-describe](references/core-describe.md) |
| Expect API    | Assertions with toBe, toEqual, matchers and asymmetric matchers | [core-expect](references/core-expect.md)     |
| Hooks         | beforeEach, afterEach, beforeAll, afterAll, aroundEach          | [core-hooks](references/core-hooks.md)       |

## Features

| Topic        | Description                                                    | Reference                                                  |
| ------------ | -------------------------------------------------------------- | ---------------------------------------------------------- |
| Mocking      | Mock functions, modules, timers, dates with vi utilities       | [features-mocking](references/features-mocking.md)         |
| Snapshots    | Snapshot testing with toMatchSnapshot and inline snapshots     | [features-snapshots](references/features-snapshots.md)     |
| Coverage     | Code coverage with V8 or Istanbul providers                    | [features-coverage](references/features-coverage.md)       |
| Test Context | Test fixtures, context.expect, test.extend for custom fixtures | [features-context](references/features-context.md)         |
| Concurrency  | Concurrent tests, parallel execution, sharding                 | [features-concurrency](references/features-concurrency.md) |
| Filtering    | Filter tests by name, file patterns, tags                      | [features-filtering](references/features-filtering.md)     |

## Advanced

| Topic        | Description                                             | Reference                                                    |
| ------------ | ------------------------------------------------------- | ------------------------------------------------------------ |
| Vi Utilities | vi helper: mock, spyOn, fake timers, hoisted, waitFor   | [advanced-vi](references/advanced-vi.md)                     |
| Environments | Test environments: node, jsdom, happy-dom, custom       | [advanced-environments](references/advanced-environments.md) |
| Type Testing | Type-level testing with expectTypeOf and assertType     | [advanced-type-testing](references/advanced-type-testing.md) |
| Projects     | Multi-project workspaces, different configs per project | [advanced-projects](references/advanced-projects.md)         |

## Testing Best Practices

### When to Mock (and When NOT to Mock)

Vitest's `vi.mock()` is powerful but can hide integration bugs if overused. Follow these guidelines:

**✅ DO Mock:**

- External network calls (HTTP APIs, databases)
- File system I/O (when testing non-I/O logic)
- Third-party services (payment processors, email services)
- System resources (timers, random number generators)

**⚠️ AVOID Mocking:**

- Internal packages you control (e.g., `vi.mock('@myapp/core')` in `@myapp/cli` tests)
- Public API wrappers when testing their delegation
- Dependencies within the same layer

### Test Layer Architecture

| Layer                 | Purpose                               | Use Mocks?                      |
| --------------------- | ------------------------------------- | ------------------------------- |
| **Unit Tests**        | Test single component in isolation    | Mock all dependencies           |
| **Integration Tests** | Test multiple components together     | Mock only external services     |
| **Public API Tests**  | Verify public exports work end-to-end | Minimal mocking (I/O only)      |
| **E2E Tests**         | Test complete user workflows          | No mocking except external APIs |

### Example: Integration Test with Minimal Mocking

```typescript
// ✅ GOOD: Tests real @myapp/core, mocks only filesystem
import * as core from "@myapp/core";
import { readFileSync } from "node:fs";

vi.mock("node:fs");

it("should process template using real core library", () => {
  vi.mocked(readFileSync).mockReturnValue("Hello {{ name }}!");

  const result = processTemplate("file.tmpl", { name: "World" });

  expect(result).toBe("Hello World!");
});
```

```typescript
// ❌ BAD: Over-mocking hides broken wiring
vi.mock("@myapp/core", () => ({
  render: vi.fn(() => "mocked"),
}));

it("calls render", () => {
  processTemplate("file.tmpl", {});
  expect(core.render).toHaveBeenCalled(); // Tests mock, not real code!
});
```

**See Also:** Use the `integration-testing` skill for comprehensive guidance on mock boundaries, test patterns, and work item testing requirements.
