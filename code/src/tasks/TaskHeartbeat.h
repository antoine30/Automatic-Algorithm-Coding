#pragma once

/**
 * @file TaskHeartbeat.h
 * @brief LLR_TSK_004 — Tâche heartbeat (clignotement LED d'état), event-driven.
 *
 * Réagit aux événements INIT/START/STOP via des handlers virtuels (aucun switch).
 * La périodicité (500 ms) est fournie par un timer logiciel FreeRTOS qui poste
 * un événement START. Autonome : ne dépend que de io_mapping (aucun driver).
 */

#include <cstdint>

#include "tasks/TaskBase.h"

class TaskHeartbeat : public TaskBase
{
public:
    TaskHeartbeat();

    TaskStatus onInit() override;  ///< INIT  : configure la LED, l'éteint.
    TaskStatus onStart() override; ///< START : inverse l'état de la LED.
    TaskStatus onStop() override;  ///< STOP  : éteint la LED.
    const char *getName() const override;

    /// @return le nombre de bascules de la LED (utile pour les tests).
    uint32_t toggleCount() const { return m_toggleCount; }

private:
    bool m_ledOn;
    uint32_t m_toggleCount;
};
