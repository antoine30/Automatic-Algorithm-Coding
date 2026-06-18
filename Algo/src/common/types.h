#ifndef COMMON_TYPES_H
#define COMMON_TYPES_H

/**
 * @file types.h
 * @brief LLR_ALG_006 — Common return/status types shared across the pipeline.
 *
 * Fixed-point arithmetic primitives (saturate, Q4.27 multiply) live in
 * LLR_ALG_000 (arithmetic_target.h); this header covers only the shared
 * status enumeration used by every stage and the pipeline assembly.
 */

#include <cstdint>

/// Pipeline status code. `OK` on success; otherwise the first failing stage.
enum class TaskStatus : int32_t
{
    OK = 0,
    ERROR = 1,
    BAD_ARGUMENT = 2,
    STAGE_BESSEL = 3,
    STAGE_PHASE = 4,
    STAGE_UNWRAP = 5
};

#endif // COMMON_TYPES_H
