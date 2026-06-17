#pragma once

/**
 * @file scheduler.h
 * @brief LLR_SCH_001 — Singleton de gestion des tâches FreeRTOS.
 *
 * NOTE : TaskCommunication (LLR_TSK_002) et TaskHeartbeat (LLR_TSK_004) sont
 * instanciées. TaskSensor (LLR_TSK_003) est définie mais NON instanciée : elle
 * requiert une implémentation concrète d'ISensor, qui n'a pas encore de LLR.
 */

#include "drivers/UartDriver.h"
#include "tasks/TaskCommunication.h"
#include "tasks/TaskHeartbeat.h"

class Scheduler
{
public:
    /// @return l'instance unique du scheduler.
    static Scheduler &getInstance();

    /// Instancie/démarre les tâches et leur envoie l'événement INIT.
    void init();

    /// Démarre l'ordonnanceur (ne retourne pas en fonctionnement normal).
    void start();

    Scheduler(const Scheduler &) = delete;
    Scheduler &operator=(const Scheduler &) = delete;

private:
    Scheduler();
};
