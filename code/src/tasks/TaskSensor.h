#pragma once

/**
 * @file TaskSensor.h
 * @brief LLR_TSK_003 — Tâche capteur, pilotée par événements.
 *
 * Lit périodiquement un capteur (ISensor). Réagit aux événements INIT/START/STOP
 * via des handlers virtuels (aucun switch). La périodicité (50 ms) est fournie
 * par un timer logiciel FreeRTOS qui poste un événement START.
 */

#include <cstddef>
#include <cstdint>

#include "interfaces/ISensor.h"
#include "tasks/TaskBase.h"

class TaskSensor : public TaskBase
{
public:
    /// @param sensor Capteur injecté par référence (injection de dépendance).
    explicit TaskSensor(ISensor &sensor);

    TaskStatus onInit() override;  ///< INIT  : init + calibration du capteur.
    TaskStatus onStart() override; ///< START : acquisition d'un échantillon.
    TaskStatus onStop() override;  ///< STOP  : passage en repos.
    const char *getName() const override;

    /// @return le nombre d'échantillons acquis (utile pour les tests).
    uint32_t sampleCount() const { return m_sampleCount; }

private:
    ISensor &m_sensor;
    static uint8_t s_sample[32]; ///< Buffer d'échantillon statique — no malloc.
    uint32_t m_sampleCount;
    bool m_running;
};
