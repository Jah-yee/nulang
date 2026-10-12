---
title: Why Nulang?
description: The benefits of Nulang compared to other languages and the goal behind the project.
---

## The Goal: A Language for Software That Survives

Nulang is an experimental language for typed, concurrent, and potentially durable computation. Ordinary actors keep state in memory; `persistent actor` opts into persistence, and `entity` declarations use an event-sourced state model by default. Actual recovery guarantees depend on the runtime path and configured store. Test restart and failure behavior on the compiler version you intend to run.

The goal is not to replace every programming language. Nulang explores what becomes possible when actors, algebraic effects, static types, and explicit state models are designed together. The language remains alpha, and integration and ecosystem maturity are not comparable to established production platforms.

---

## Nulang vs Erlang/Elixir

Both languages share the actor model, supervision trees, and "let it crash" philosophy. The differences:

| | Nulang | Erlang/Elixir |
|---|---|---|
| **Type system** | Static, HM-inferred, row-polymorphic | Dynamic (Erlang) / Gradual (Elixir) |
| **Effects** | Algebraic effects, compile-time checked | No effect tracking |
| **Execution** | Bytecode VM + Cranelift JIT; experimental WASM and native AOT | Mature BEAM VM + JIT, garbage-collected |
| **Memory model** | Per-actor heaps, ORCA GC | Shared heap, per-process GC |
| **AI library** | Optional nulang-ai library with memory | Library-level (Nx, Bumblebee) |

**Takeaway**: Nulang may appeal if you want native typed effects and capability checking alongside actor supervision. Erlang/Elixir and OTP are substantially more proven for production fault tolerance. Nulang performance must be measured on representative workloads, not assumed from its JIT.

---

## Nulang vs Rust

Rust and Nulang share a focus on safety and performance, but their domains differ:

| | Nulang | Rust |
|---|---|---|
| **Concurrency model** | Actors + messages | async/await, channels, Arc&lt;Mutex&lt;T&gt;&gt; |
| **Distribution** | Experimental actor transport and CRDT runtime primitives | Libraries and protocols such as gRPC; established ecosystem |
| **Fault tolerance** | Actor supervision and restart policies | `Result`, panic unwinding (by default), and application-specific supervision/restart strategies |
| **Workflows** | Experimental durable workflow language/runtime support | Libraries and engines such as Temporal |
| **Type safety** | HM inference + capabilities | Ownership + borrows + lifetimes |

**Takeaway**: Rust is the stronger choice for mature systems programming, ecosystem breadth, and predictable low-level control. Nulang experiments with higher-level actors and supervision; its multi-node distribution remains experimental.

---

## Nulang vs Go

Go's strength is simplicity. Nulang's strength is correctness under failure:

| | Nulang | Go |
|---|---|---|
| **Concurrency** | Actors with supervision | Goroutines + channels |
| **Error handling** | Pattern matching, supervision | `if err != nil` |
| **Type system** | HM inference, row polymorphism, ADTs | Static structural interfaces and generics (since Go 1.18) |
| **Effects** | Compile-time effect tracking | No effect system |
| **Distribution** | Experimental multi-node actor runtime | Library/protocol-level |

**Takeaway**: Go is the pragmatic production default for many network services. Nulang makes failure handling and effects more explicit in its language model, but has not demonstrated lower operational burden in production deployments.

---

## Nulang vs Python/TypeScript (for AI)

The AI ecosystem has converged on Python and TypeScript, but both languages were designed before LLMs existed:

| | Nulang | Python/TypeScript |
|---|---|---|
| **Agent declaration** | Declarative `agent` keyword | Library objects (LangChain, etc.) |
| **Memory** | Experimental, feature-gated agent-memory primitives | Broad libraries and databases; persistence often external |
| **Multi-agent** | Experimental agent pipelines and supervisor patterns | Mature orchestration libraries and agent frameworks |
| **Determinism** | Effects tracked by the type system; external replay still requires explicit safeguards | Determinism and replay depend on framework and application design |
| **Persistence** | Persistence APIs and experimental higher-level recovery semantics | Widely deployed databases and workflow engines |

**Takeaway**: Python and TypeScript have stronger provider support, tools, and deployment paths today. Nulang's declarative agent primitives are an interesting experiment, not yet an equivalent production replacement.

---

## The Bet: Primitives Over Frameworks

Every decade brings new AI models, new cloud providers, and new orchestration frameworks. The Nulang bet is that a small set of primitives — actors, effects, capabilities, state, identity, messages — will outlast all of them.

- **Actors** were meaningful in 1973 (Hewitt et al.) and will be meaningful in 2073.
- **Algebraic effects** generalize exceptions, async/await, generators, and state — all in one mechanism.
- **Reference capabilities** help constrain aliasing and shared mutation; Nulang also uses actor-local memory management and garbage collection.
- **Durable state** can survive restarts when a persistent store and the required recovery path are configured and verified; it does not imply automatic cross-node failover or exactly-once external effects.

Nulang freezes these primitives in a [Frozen Core](https://github.com/nulang-org/nulang/blob/main/GOVERNANCE.md) and builds everything else — AI, cloud services, billing, multi-tenancy — as evolvable layers.

---

## When to Use Nulang

- You're prototyping explicit state and recovery models and can validate their behavior against failure tests.
- You need **fault tolerance** but don't want to learn OTP from scratch.
- You want **static types** that catch bugs before they reach production.
- You're building **AI agents** that need memory, tool use, and multi-agent coordination.
- You want to explore a language/runtime approach to durable and distributed applications, with experimental features clearly identified.

## When Not to Use Nulang

- You need a mature ecosystem with thousands of libraries. (Nulang is alpha.)
- You're building a CLI tool or a simple script. (Use Rust, Go, or Python.)
- You need Web/React/SPA frontend support. (Use TypeScript.)
- You're under a tight deadline with no tolerance for alpha software.

---

## Getting Started

For production-critical workloads, continue to prefer proven languages and runtimes until Nulang's alpha behavior is verified for your requirements.

[Install Nulang](/getting-started/installation/) and follow the [Quick Start](/getting-started/quick-start/) guide to write your first actor.

The [source code is on GitHub](https://github.com/nulang-org/nulang) under the Apache 2.0 license.
