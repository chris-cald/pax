---
name: integration-testing
description: Integration testing best practices for TypeScript/JavaScript projects. Use when writing tests for public APIs, cross-package integration, end-to-end workflows, or testing dependencies between components. Guides mock boundaries, when NOT to mock, and test layer architecture.
metadata:
  author: templjs
  version: 1.0.0
  created: 2026-03-06
---

# Integration Testing

Integration testing verifies that multiple components work together correctly. Unlike unit tests that isolate a single component with mocks, integration tests exercise real implementations across boundaries.

**Key Principle**: Don't mock what you're testing. Mock external dependencies (APIs, databases), but use real implementations for internal components.

## When to Use

Use integration tests when:

- **Testing public API exports** - Verify that wrapper functions delegate to implementations
- **Cross-package integration** - Test that packages call each other correctly
- **Multi-component workflows** - Verify end-to-end processes (e.g., tokenize → parse → render)
- **Factory patterns** - Ensure factory functions return working implementations

Do NOT use integration tests for:

- **Implementation internals** - Use unit tests to verify individual class/function logic
- **Error-only scenarios** - Mock-based unit tests are sufficient for error path coverage

## Testing Layer Architecture

| Layer                 | Purpose                               | Mocking Strategy                |
| --------------------- | ------------------------------------- | ------------------------------- |
| **Unit Tests**        | Test single component in isolation    | Mock all dependencies           |
| **Integration Tests** | Test multiple components together     | Mock only external services     |
| **Public API Tests**  | Verify public exports work end-to-end | Minimal mocking (I/O only)      |
| **E2E Tests**         | Test complete user workflows          | No mocking except external APIs |

## Mock Boundaries

### ✅ DO Mock

- External network calls (HTTP APIs, databases)
- File system I/O (when testing non-I/O logic)
- Third-party services (payment processors, email services)
- System resources (timers, random number generators)

### ⚠️ AVOID Mocking

- **Internal packages you control** (e.g., `vi.mock('@templjs/core')` in CLI tests)
- **Public API wrappers** testing real implementations
- **Dependencies within the same layer** (core components calling each other)

## Instructions

### Step 1: Identify Test Type

Determine which test layer is appropriate:

- Testing a single class method? → Unit test
- Testing multiple components together? → Integration test
- Testing a public API export? → Public API test
- Testing a complete user workflow? → E2E test

### Step 2: Define Mock Boundaries

For integration tests:

1. List all components involved in the test
2. Identify external dependencies (APIs, databases, file system)
3. Mock ONLY external dependencies
4. Use real implementations for internal components

### Step 3: Write the Test

#### Pattern 1: Public API Integration Test

```typescript
// ✅ GOOD: Tests real implementation without mocking internal logic
import { renderTemplate } from "@templjs/core";

describe("renderTemplate public API", () => {
  it("should render template with data", () => {
    const template = "Hello {{ name }}!";
    const data = { name: "World" };

    const result = renderTemplate(template, data);

    expect(result).toBe("Hello World!");
  });

  it("should return errors without throwing", () => {
    const template = "Invalid {{ syntax";
    const data = {};

    const result = renderTemplate(template, data);

    expect(result.errors).toBeDefined();
    expect(result.errors.length).toBeGreaterThan(0);
  });
});
```

#### Pattern 2: Cross-Package Integration Test

```typescript
// ✅ GOOD: Real @templjs/core import, tests real delegation
import * as core from "@templjs/core";

// Mock ONLY external I/O (file system)
vi.mock("node:fs", () => ({
  readFileSync: vi.fn(() => "Hello {{ name }}!"),
}));

describe("CLI processTemplate", () => {
  it("should delegate to core.renderTemplate", () => {
    const result = processTemplate("/path/to/template", { name: "Test" });

    expect(result).toBe("Hello Test!");
  });
});
```

#### Anti-Pattern: Over-Mocking

```typescript
// ❌ BAD: Mocks internal package, hides implementation gaps
vi.mock("@templjs/core", () => ({
  renderTemplate: vi.fn(() => "mocked result"),
}));

describe("CLI processTemplate", () => {
  it("should call renderTemplate", () => {
    processTemplate("/path", {});

    expect(core.renderTemplate).toHaveBeenCalled(); // Tests mock, not real code!
  });
});
```

### Step 4: Validate Test Coverage

**Before closing a work item**, verify:

1. **Component tests exist** - Unit tests for implementation classes/functions
2. **Integration tests exist** - Tests for multi-component interactions
3. **Public API tests exist** - Every exported function/class has integration test
4. **E2E tests exist** (if applicable) - Manual or automated end-to-end verification

**Checklist**:

- [ ] All unit tests pass (component implementation)
- [ ] Integration tests exist for cross-component flows
- [ ] Every public export (`export { X } from './index'`) has a test
- [ ] Manual E2E verification completed (for CLI: run actual commands)
- [ ] Tests use real implementations (minimal mocking)

## Common Scenarios

### Scenario 1: Testing Wrapper Functions

**Problem**: Public API has wrapper functions that were stubbed during initial implementation.

**Solution**: Write integration tests that call the wrapper and verify it delegates correctly.

```typescript
// src/index.ts
export function renderTemplate(template: string, data: object) {
  // Previously threw "not yet implemented"
  const tokens = tokenize(template);
  const ast = parse(tokens);
  return render(ast, data);
}

// test/index.test.ts
describe("renderTemplate", () => {
  it("should tokenize, parse, and render", () => {
    const result = renderTemplate("Hello {{ name }}!", { name: "World" });
    expect(result).toBe("Hello World!");
  });
});
```

### Scenario 2: Testing CLI Commands

**Problem**: CLI tests mock the entire core library, hiding broken wiring.

**Solution**: Import real core library, mock only file system I/O.

```typescript
import * as core from "@templjs/core";
import { readFileSync } from "node:fs";

vi.mock("node:fs");

describe("CLI render command", () => {
  it("should read template and render with data", () => {
    vi.mocked(readFileSync).mockReturnValue("Hello {{ name }}!");

    const result = renderCommand({
      template: "file.tmpl",
      data: { name: "Test" },
    });

    expect(result).toBe("Hello Test!");
  });
});
```

### Scenario 3: Testing Factory Functions

**Problem**: Factory functions return placeholder objects instead of real implementations.

**Solution**: Test that factory returns working object by calling its methods.

```typescript
describe("createRenderer", () => {
  it("should return functional Renderer instance", () => {
    const renderer = createRenderer();
    const ast = { type: "root", children: [] };
    const data = {};

    const result = renderer.render(ast, data);

    expect(result).toBeDefined();
    expect(typeof result).toBe("string");
  });
});
```

## Troubleshooting Example

### Problem: "Test passes but real code is broken"

**Diagnosis**: Over-mocking. Tests mock internal dependencies, hiding broken wiring.

**Solution**:

1. Identify what's being mocked (`vi.mock()` calls)
2. Remove mocks for internal packages/modules
3. Mock only external I/O (filesystem, network, databases)
4. Re-run tests - they should now fail, revealing the bug

### Problem: "How do I know what to mock?"

**Decision Tree**:

1. Is it in a different repository? → Mock it
2. Is it a network call / database / file system? → Mock it
3. Is it in your codebase? → Use real implementation
4. Is it a system resource (timer, random)? → Mock it if needed for determinism

## References

- Project how-to: `docs/how-to/integration-testing.md`
- ADR-006: Testing Strategy (`docs/adr/006-testing.md`)
- Work Item Agent: `backlog/AGENTS.md` (testing requirements)
  Result: Expected outcome

## Troubleshooting

**Error:** Common error message
**Cause:** Why it happens
**Solution:** How to fix it
