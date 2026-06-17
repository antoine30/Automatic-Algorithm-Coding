/**
 * @file IEvent.cpp
 * @brief Definition of the singleton event instances (no allocation).
 */

#include "IEvent.h"

namespace events
{
const InitEvent kInit;
const StartEvent kStart;
const StopEvent kStop;
} // namespace events
