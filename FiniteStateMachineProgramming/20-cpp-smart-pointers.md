# 20 — FSM in Modern C++: Smart Pointers and RT

[← 19](19-wcet-discipline.md) | [Next: Rules →](21-design-rules.md)

---

## The Problem with Standard Smart Pointers in RT

Standard smart pointers violate the 8 rules:

| Smart pointer | RT violation | WCET consequence |
|--------------|-------------|-----------------|
| `std::shared_ptr<T>` | R2: make_shared calls `new` (heap). Atomic reference counter on every copy | Unbounded WCET. `atomic_fetch_add` on every copy: ~10 cycles each |
| `shared_ptr::reset()` | R2: calls `delete` + destructor if use_count reaches 0 | Destructor WCET unbounded |
| `std::vector<T>` | R2: reallocation on capacity exceeded | Unbounded WCET on `push_back` |
| `std::function<>` | R2: heap for closures > ~16 bytes | Unbounded WCET, SBO not guaranteed |

## Solution 1 — unique_ptr on Static Memory (zero overhead)

```cpp
// Static storage — no heap allocation, WCET = 0
alignas(PiezoCtx) static std::byte g_ctx_storage[sizeof(PiezoCtx)];

// Placement new — no heap, WCET = 0
PiezoCtx* raw = new(g_ctx_storage) PiezoCtx{};

// Null deleter — no delete at destruction
struct NoDelete { void operator()(PiezoCtx*) noexcept {} };

// unique_ptr with NoDelete = zero overhead after optimization
// sizeof(unique_ptr<T, NoDelete>) == sizeof(T*) guaranteed
std::unique_ptr<PiezoCtx, NoDelete> ctx{raw};

ctx->freq = 40000.0f;  // zero overhead, identical to raw pointer
```

## Solution 2 — Static Pool (O(1) bounded allocation)

```cpp
template<typename T, std::size_t N>
class StaticPool {
    alignas(T) std::byte     storage_[N * sizeof(T)];
    std::array<bool, N>      used_{};
    std::size_t              next_{0};

public:
    // Allocation — O(N), N known at compile time
    [[nodiscard]] T* acquire() noexcept {
        for (std::size_t i = 0; i < N; ++i) {
            std::size_t idx = (next_ + i) % N;
            if (!used_[idx]) {
                used_[idx] = true;
                next_ = (idx + 1) % N;
                return new(&storage_[idx * sizeof(T)]) T{};
            }
        }
        return nullptr;  // pool exhausted — detectable
    }

    // Release — O(1)
    void release(T* p) noexcept {
        auto idx = (reinterpret_cast<std::byte*>(p) - storage_) / sizeof(T);
        p->~T();
        used_[idx] = false;
    }
};

static StaticPool<FsmEvent, 32> g_event_pool;

struct PoolDeleter {
    void operator()(FsmEvent* p) noexcept { g_event_pool.release(p); }
};
using EventPtr = std::unique_ptr<FsmEvent, PoolDeleter>;
```

## The FSM as a C++ Class

```cpp
class PiezoFsm {
public:
    explicit PiezoFsm(FpgaDriver& fpga, OsalQueue& queue) noexcept
        : fpga_{fpga}, queue_{queue} {}

    PiezoFsm(const PiezoFsm&)            = delete;  // exclusive ownership
    PiezoFsm& operator=(const PiezoFsm&) = delete;

    void process(const FsmEvent& ev) noexcept { /* ... */ }

private:
    State_t     state_{State::Off};   // owned value
    float       freq_{};              // owned value
    FpgaDriver& fpga_;                // reference — no copy
    OsalQueue&  queue_;               // reference — no copy
};

// Static instantiation — zero heap
static FpgaDriver  g_fpga{};
static OsalQueue   g_queue{};
static PiezoFsm    g_fsm{g_fpga, g_queue};
```

## Transition Table as constexpr

```cpp
constexpr Transition k_run_table[] = {
    { EvtType::AdcReady,
      [](const Ctx& c, const FsmEvent&) noexcept {
          return c.voltage_mv > c.vmax; },
      [](Ctx& c, const FsmEvent&) noexcept { power_cut(c); },
      State::Fault },

    { EvtType::CmdStop,
      nullptr,   // guard always true if nullptr
      [](Ctx& c, const FsmEvent&) noexcept { ramp_down(c); },
      State::Cooldown },
};
// constexpr = stored in ROM, zero runtime overhead
```

## Allowed vs Forbidden in RT C++

| **Allowed** | **Forbidden** |
|------------|--------------|
| `std::array<T,N>` | `std::shared_ptr` |
| `std::span<T>` | `std::vector`, `std::string` |
| `std::optional<T>` | `std::function<>` |
| `unique_ptr<T, NoDelete>` | `throw / try / catch` |
| `constexpr / consteval` | `dynamic_cast` |
| `[[nodiscard]] + noexcept` | `new / delete` directly |
| `std::atomic<T>` | Virtual functions in hot path |
| Stateless lambdas | `std::any` |

---

*[← 19](19-wcet-discipline.md) | [Next: Rules →](21-design-rules.md)*
