# Dynamic Linking & Loading — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Dynamic Linking & Loading** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. ABI Compatibility and the soname Contract

An **API** is a source-level promise: this header, this function signature. An **ABI** is a *binary* promise: this symbol with this calling convention, this struct laid out exactly so, this version. A library can keep its API (recompile-and-it-works) while breaking its ABI (the *already-compiled* binary now misbehaves). ABI breaks are silent and deadly because no compiler catches them — the old binary just reads a struct field at the wrong offset.

The **soname** encodes the ABI promise. `libssl.so.3` means "ABI generation 3." Binaries record the soname they need (`DT_NEEDED: libssl.so.3`). When you make an **ABI-incompatible** change — remove/change a symbol, reorder a public struct, change a calling convention — you must **bump the soname** (`.so.3` → `.so.4`). Now old binaries (needing `.so.3`) and new binaries (needing `.so.4`) can coexist on one system, each finding its own real file. ABI-*compatible* additions (new symbols, with versioning) keep the soname.

Getting this wrong *is* **dependency hell / DLL hell**: app X needs `libfoo.so.3`, app Y needs an incompatible build that overwrote it, and now one of them is broken. Distros invest enormous effort (soname discipline, symbol versioning, side-by-side installs) precisely to keep dependency hell at bay.

### 2. Startup Cost at Scale: Why Many `.so`s = Slow Start

Every shared library the loader must process costs: open the file, `mmap` it, parse its dynamic section, recursively load *its* dependencies, run relocations, run constructors. A binary with 5 libraries is cheap; one with 80 (a typical desktop app pulling Qt/GTK + dozens of transitive deps) spends real milliseconds in the loader before `main`.

The dominant costs are **relocation processing** (especially with many symbols and eager binding) and **symbol lookup** across many libraries (hash-table probes per symbol, times thousands of symbols). This is why:

- **`prelink`** existed: it pre-computed library load addresses and relocations so the loader could skip work. It's effectively dead because pre-assigning fixed addresses fights **ASLR** (the whole point of which is *random* addresses). Security won; prelink lost.
- **`-z now` makes startup slower but latency predictable**; lazy binding spreads the cost.
- **Static linking and AOT win cold starts.** A static binary skips the loader's find/map/resolve loop almost entirely. This is decisive for **serverless** (a function invoked from cold pays loader cost on every cold start) and **CLIs** (launched millions of times). Go's static binaries and GraalVM native-image exist substantially for this reason: trade build complexity and binary size for near-zero startup.

The rule: **if cold-start latency is a product metric, fewer shared libraries — ideally static or AOT — is the lever.** If memory sharing across many long-lived processes is the metric, dynamic wins.

### 3. The Windows Loader: IAT, Search Order, Hijacking, Delay-Load

Windows uses the same *ideas* with different names and a different security history.

- **IAT (Import Address Table):** Windows' GOT. The PE header lists imported DLLs and functions; the loader fills the IAT with resolved pointers. Calls go `call [IAT_slot]`. (Windows historically bound eagerly; lazy-ish behavior comes via delay-load.)
- **DLL search order:** the loader searches a sequence of directories for each needed DLL. The dangerous historical default included **the application's directory and the current working directory early in the order.** That is the root of **DLL hijacking / planting**: if an attacker can drop `version.dll` (or any DLL the app loads by name) into a directory searched *before* the legitimate one — say, the folder a user double-clicked an installer from — the app loads and executes the attacker's DLL with the app's privileges. This is a real, repeatedly-exploited class (installers run from `~/Downloads` are a classic vector). Mitigations: `SetDefaultDllDirectories`/`SafeDllSearchMode`, loading with **fully-qualified paths**, `LOAD_LIBRARY_SEARCH_*` flags, and signing.
- **Delay-loading:** mark a DLL delay-loaded and the loader doesn't resolve it until the first call into it. Speeds startup and lets an app run when an *optional* DLL is absent (you catch the structured exception and degrade gracefully). The cost is that a missing/incompatible DLL surfaces *later*, mid-feature, instead of at launch.

The cultural difference: Linux dependency hell is mostly about *versions*; Windows DLL hell historically added a *security* dimension (the search order) that Linux's RPATH/cache model largely avoids.

### 4. JVM Class Loading: Loading, Linking, Initialization

The JVM is a dynamic linker for bytecode, and it makes the phases explicit:

1. **Loading:** a classloader finds the `.class` bytes (from disk, a JAR, the network, generated in memory) and creates a `Class` object.
2. **Linking**, in three sub-phases:
   - **Verification:** check the bytecode is well-formed and type-safe (no stack overflows of the operand stack, no illegal casts). This is a big chunk of JVM startup cost.
   - **Preparation:** allocate static fields and set them to *default* values (0/null) — not initializers yet.
   - **Resolution:** turn symbolic references (constant-pool entries like "the method `String.length`") into direct references — the JVM's analogue of relocation, done lazily per reference.
3. **Initialization:** run static initializers and static field assignments, *the first time the class is actively used*. This is where your `static {}` blocks fire.

This lazy, per-class pipeline is exactly dynamic linking, one class at a time, with verification bolted on for safety.

### 5. The Classloader Hierarchy and Parent Delegation

Classloaders form a tree: **Bootstrap** (core `java.*`) → **Platform/Extension** → **Application/System** (your classpath) → any **custom** loaders (app servers, plugin frameworks, OSGi). The default rule is **parent delegation**: when asked to load a class, a loader first asks its *parent*, and only loads the class itself if the parent can't. This guarantees core classes (`java.lang.Object`) are loaded once by the bootstrap loader and can't be shadowed by application code — a security and correctness property.

Crucially, **class identity = (fully-qualified name, defining classloader).** The *same* class file loaded by *two different* classloaders yields two distinct `Class` objects that are **not assignment-compatible** — assigning one to a variable typed by the other throws `ClassCastException` even though "they're the same class." This is by design (it's how app servers isolate two web apps that bundle different versions of the same library) and a frequent source of baffling `ClassCastException: Foo cannot be cast to Foo` errors.

### 6. `ClassNotFoundException` vs `NoClassDefFoundError`

A perennial interview and debugging distinction:

- **`ClassNotFoundException`** (a checked `Exception`): thrown by *explicit* loading — `Class.forName("com.x.Y")`, `loader.loadClass(...)`, reflection — when the bytes can't be found. The code asked for a class by name and the loader couldn't locate it.
- **`NoClassDefFoundError`** (an `Error`): thrown when the JVM needs a class to *link or execute* code that referenced it directly (a `new`, a field type, a superclass) and the class is now missing **or failed to initialize**. A common trap: a class's static initializer throws, the class is marked erroneous, and *every later use* gets `NoClassDefFoundError` — masking the real cause (the original initializer exception). The presence-at-compile, absence-at-run shape is the signature: usually a packaging/classpath mismatch between build and run.

### 7. Classloader Leaks: A Production Memory Bug

In a long-running container (Tomcat, an app server) you redeploy an app: the old app's classloader and all its classes and statics *should* become garbage and be collected. A **classloader leak** is when they can't be, because some object *outside* the app's classloader still references *into* it. The whole classloader is then pinned, retaining **every class it loaded and every static field** — often tens of megabytes per redeploy. Redeploy ten times, OOM.

Classic culprits, all "something with a longer life than your app holds a reference into your app":

- A **`ThreadLocal`** on a pooled (container-owned) thread holding an app object.
- A **JDBC driver** registered in the container-wide `DriverManager`.
- A **timer/thread** (`java.util.Timer`, an `ExecutorService`) started by the app but never stopped, whose thread's context classloader pins the app loader.
- A static cache in a *shared* (container) library keyed by app classes.
- Singletons registered in JVM-wide registries (MBeans, shutdown hooks, security providers).

The fix is lifecycle discipline: on undeploy, deregister drivers, cancel timers, clear `ThreadLocal`s, shut down executors, and unregister from any JVM-wide singleton. Tools: a heap dump + "find the GC root path to the leaked classloader" in a profiler. This is the JVM's version of "`dlclose` didn't actually unload" from the senior level — the runtime kept a reference, so the unload didn't happen.

---

## Code Examples

### Inspect and reason about a soname

```text
$ readelf -d /usr/lib/.../libssl.so.3 | grep SONAME
 0x...  (SONAME)   Library soname: [libssl.so.3]
$ readelf -d ./myapp | grep NEEDED
 0x...  (NEEDED)   Shared library: [libssl.so.3]      <- app pinned to ABI gen 3
```

If OpenSSL bumps to `libssl.so.4` (ABI break), `myapp` keeps needing `.so.3`; both can be installed. Overwriting `.so.3`'s file with `.so.4` content is exactly how dependency hell starts.

### Measure loader cost

```text
$ LD_DEBUG=statistics ./heavy_app 2>&1 | grep -A6 "runtime linker statistics"
   total startup time in dynamic loader: 7,300,000 cycles
   time needed for relocation: 4,100,000 cycles
   number of relocations: 18,442
   ...
# Compare against a statically linked or AOT build to quantify the win.
```

This turns "dynamic linking is slow" from folklore into a number you can put in a perf budget.

### Java: the two failures, side by side

```java
// ClassNotFoundException — explicit, by name, not found:
try { Class.forName("com.example.NotShipped"); }
catch (ClassNotFoundException e) { /* asked by name, loader couldn't find it */ }

// NoClassDefFoundError — present at compile, gone (or failed init) at run:
//   Compiled with Helper on the classpath; run without it:
public class App {
    public static void main(String[] a) {
        new Helper();   // direct reference -> NoClassDefFoundError if Helper missing at run
    }
}
// Also fires if Helper's static initializer THREW the first time it was used.
```

### Java: a classloader leak and its fix

```java
// LEAK: a container-owned thread's ThreadLocal pins this app's classloader.
public class Cache {
    private static final ThreadLocal<byte[]> BUF = ThreadLocal.withInitial(() -> new byte[1<<20]);
    // On a pooled request thread, BUF retains an app-loaded object forever ->
    // the app's classloader can never be GC'd after undeploy.
}

// FIX: clear it on undeploy (e.g. ServletContextListener.contextDestroyed):
public void contextDestroyed(ServletContextEvent e) {
    Cache.BUF.remove();                 // release ThreadLocal
    java.sql.DriverManager.deregisterDriver(myDriver);  // unregister JDBC driver
    myExecutor.shutdownNow();           // stop app-started threads
}
```

### Windows: load a DLL safely (avoid hijacking)

```c
// UNSAFE: name only — subject to the search order (CWD, app dir, ...):
HMODULE h = LoadLibraryA("plugin.dll");

// SAFER: restrict the search to system + the directory of the module you trust,
// and/or pass a fully-qualified path:
SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_SYSTEM32 | LOAD_LIBRARY_SEARCH_APPLICATION_DIR);
HMODULE h2 = LoadLibraryExA("C:\\Program Files\\MyApp\\plugin.dll",
                            NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
```

---

## Coding Patterns

### Pattern 1: Choose the linking model per workload, with numbers

Cold-start-bound (serverless, CLI) → lean toward static/AOT. Patch-cadence-bound or RAM-bound (many long-lived processes sharing big libs) → dynamic. Decide with `LD_DEBUG=statistics` and cold-start measurements, not vibes.

### Pattern 2: Govern ABI with sonames and version scripts

Treat your shared library's exported symbols as a published contract. Use a linker **version script** to control exports, add symbols compatibly (new versions), and **bump the soname** on any ABI break. CI should diff the exported symbol set between releases.

### Pattern 3: Load DLLs by full path and restrict search dirs

On Windows, never `LoadLibrary("name")` for anything an attacker could shadow. Use `SetDefaultDllDirectories`, fully-qualified paths, and signed binaries. Treat the search order as hostile.

### Pattern 4: Lifecycle every JVM-wide registration

For anything an app registers in a JVM-wide singleton (drivers, MBeans, shutdown hooks, `ThreadLocal`s on pooled threads, executors, timers), register on startup and **explicitly unregister on shutdown/undeploy.** This is the entire defense against classloader leaks.

---

## Best Practices

1. **Make startup cost a measured budget**, especially for cold-start-sensitive workloads; reach for static/AOT when the numbers justify it.
2. **Don't static-link security-critical libraries (`libssl`/`libcrypto`) carelessly** — you're opting *out* of fleet-wide patching. If you do, own the rebuild-and-redeploy responsibility explicitly.
3. **Practice soname discipline.** Compatible change → keep soname + version new symbols. Incompatible change → bump soname. Never overwrite an in-use soname's file with incompatible content.
4. **On Windows, treat the DLL search order as attack surface.** Full paths, restricted search directories, signing; audit what your app loads by bare name.
5. **In the JVM, deregister everything on undeploy** and heap-dump-diff after redeploys to catch classloader leaks before they OOM production.
6. **Know your `ClassNotFoundException` vs `NoClassDefFoundError` first move:** the former is a packaging/lookup miss; the latter is "present at compile, gone or init-failed at run" — check the *first* initializer exception, which the later errors mask.
7. **Keep dependency trees shallow and pinned.** Fewer transitive `.so`s/DLLs/JARs means faster start, smaller attack surface, and less dependency hell.

---

## Edge Cases & Pitfalls

**Pitfall: a "compatible" change that's secretly an ABI break.** Adding a field to the *middle* of a public struct, changing an enum's values, changing a function's calling convention, or inlining a previously-out-of-line function all break ABI while the API looks unchanged. No compiler warns. Tools like `abidiff` (libabigail) catch these; manual review usually doesn't.

**Pitfall: `RUNPATH` `$ORIGIN` security and portability.** `$ORIGIN` in RPATH/RUNPATH lets a binary find libraries *relative to itself* (great for bundled apps). But a writable `$ORIGIN` directory, or an attacker-controllable RPATH, becomes a code-execution vector — the Linux analogue of DLL planting. Privileged binaries ignore some of these for that reason.

**Pitfall: prelink nostalgia.** Don't try to reintroduce prelink-style fixed addresses for speed; you'd be disabling ASLR. The modern answer to startup cost is static/AOT or fewer libraries, not defeating address randomization.

**Pitfall: Windows delay-load hiding a missing dependency until a customer hits it.** A delay-loaded DLL that's absent launches fine and crashes the *one* customer who uses that feature, with a stack deep in the loader. Decide deliberately which dependencies are optional, and handle the delay-load failure (structured exception) gracefully.

**Pitfall: `ClassCastException: Foo cannot be cast to Foo`.** Two classloaders loaded the same class file → two distinct `Class` identities. Almost always a classloader-hierarchy or duplicate-JAR problem (the class is on both the parent and child classpath, or two web apps share it incorrectly). The fix is classpath hygiene, not casting tricks.

**Pitfall: static initializer failure poisoning a class.** If `static {}` throws once, the class enters an erroneous state and *every* subsequent reference throws `NoClassDefFoundError` — with no mention of the original cause. Always capture and log the *first* `ExceptionInInitializerError`; the later `NoClassDefFoundError`s are red herrings.

**Pitfall: `LD_LIBRARY_PATH` in production.** Convenient, but it's process-environment state that's easy to set wrong, easy to leak between services, and ignored for setuid binaries. Prefer RPATH/RUNPATH (`$ORIGIN` for bundles) or proper installation; reserve `LD_LIBRARY_PATH` for debugging.

---

## Apply it

1. Define the user or business outcome that **Dynamic Linking & Loading** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Dynamic Linking & Loading?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
