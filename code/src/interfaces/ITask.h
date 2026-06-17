#pragma once

/**
 * @file ITask.h
 * @brief LLR_ITF_001 — Interface abstraite des tâches FreeRTOS (event-driven).
 *
 * Une tâche est pilotée par événements : elle reçoit des objets IEvent
 * (cf. LLR_ITF_004) et chaque événement exécute le code associé en appelant
 * l'un des handlers virtuels ci-dessous. Le type d'événement n'est jamais
 * résolu par un switch/case : c'est IEvent::execute() qui sélectionne le
 * handler (double-dispatch).
 */

#include <cstdint>

/// Code de retour des traitements de tâche.
enum class TaskStatus : uint8_t
{
    OK = 0,
    ERROR = 1,
    TIMEOUT = 2,
    NOT_INITIALIZED = 3,
    BUSY = 4
};

/**
 * @brief Interface 100% abstraite que toute tâche FreeRTOS doit implémenter.
 *
 * Les handlers sont appelés via IEvent::execute() (double-dispatch). Aucune
 * donnée membre, aucune implémentation : interface pure.
 */
class ITask
{
public:
    virtual ~ITask() = default;

    /// Exécuté sur l'événement INIT.
    virtual TaskStatus onInit() = 0;

    /// Exécuté sur l'événement START (démarre / fait tourner le process).
    virtual TaskStatus onStart() = 0;

    /// Exécuté sur l'événement STOP.
    virtual TaskStatus onStop() = 0;

    /// @return le nom de la tâche (pour les logs).
    virtual const char *getName() const = 0;
};
