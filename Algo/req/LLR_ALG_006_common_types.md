# LLR_ALG_006 — Common Types and Status Codes

## Level : LOW LEVEL
## Parent HLR : HLR_003
## Version : 4.0
## Depends on : LLR_ALG_000

## Files to Generate
- src/common/types.h

---

## 1. Purpose

Defines the shared status/return type used across pipeline stages. Fixed-point
arithmetic primitives (saturate, Q4.27 multiply) live in LLR_ALG_000
(arithmetic_target.h); this LLR covers only the common enumerations/types that
every algorithm module and the pipeline assembly depend on.

---

## 2. TaskStatus

```cpp
enum class TaskStatus : int32_t {
    OK           = 0,  ///< success
    ERROR        = 1,  ///< generic failure
    BAD_ARGUMENT = 2,  ///< null pointer or out-of-range length
    STAGE_BESSEL = 3,  ///< failure in spur removal stage
    STAGE_PHASE  = 4,  ///< failure in phase computation stage
    STAGE_UNWRAP = 5   ///< failure in phase unwrap stage
};
```

`process()` returns `OK` on success, otherwise the identifier of the first
failing stage.

---

## 3. Constraints

- Header-only.
- Fixed-width underlying type (int32_t).
- No dependency beyond `<cstdint>`.

---

## 4. Test Requirements

| Test ID | Check                                          |
|---------|------------------------------------------------|
| T001    | TaskStatus::OK == 0                            |
| T002    | distinct values per stage, fixed-width int32   |
