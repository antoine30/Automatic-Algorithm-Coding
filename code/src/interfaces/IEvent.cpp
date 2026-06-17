/**
 * @file IEvent.cpp
 * @brief Définition des instances singleton d'événements (aucune allocation).
 */

#include "IEvent.h"

namespace events
{
const InitEvent kInit;
const StartEvent kStart;
const StopEvent kStop;
} // namespace events
