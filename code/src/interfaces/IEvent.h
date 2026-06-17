#pragma once

/**
 * @file IEvent.h
 * @brief LLR_ITF_004 — Événement asynchrone livré à une tâche.
 *
 * Le routage d'un événement vers son traitement se fait UNIQUEMENT par méthode
 * virtuelle (double-dispatch / visiteur) : IEvent::execute() appelle le handler
 * correspondant de la tâche. Aucun switch/case, aucune chaîne if/else sur
 * EventId. Ajouter un événement = ajouter une classe, jamais éditer un aiguillage.
 */

#include <cstdint>

#include "ITask.h"

/// Identifiants d'événements (debug / log uniquement — PAS pour l'aiguillage).
enum class EventId : uint8_t
{
    INIT = 0,  ///< Initialise la tâche.
    START = 1, ///< Démarre / fait tourner le process.
    STOP = 2   ///< Arrête le process.
};

/**
 * @brief Événement abstrait. Le type concret choisit le handler à appeler.
 */
class IEvent
{
public:
    virtual ~IEvent() = default;

    /// @return l'identifiant de l'événement (debug/log, jamais pour dispatch).
    virtual EventId id() const = 0;

    /// Double-dispatch : exécute le code associé en appelant le handler virtuel
    /// adéquat de la tâche. Aucun switch/case.
    virtual TaskStatus execute(ITask &task) const = 0;
};

/// Événement INIT → ITask::onInit().
class InitEvent final : public IEvent
{
public:
    EventId id() const override { return EventId::INIT; }
    TaskStatus execute(ITask &task) const override { return task.onInit(); }
};

/// Événement START → ITask::onStart().
class StartEvent final : public IEvent
{
public:
    EventId id() const override { return EventId::START; }
    TaskStatus execute(ITask &task) const override { return task.onStart(); }
};

/// Événement STOP → ITask::onStop().
class StopEvent final : public IEvent
{
public:
    EventId id() const override { return EventId::STOP; }
    TaskStatus execute(ITask &task) const override { return task.onStop(); }
};

/**
 * @brief Instances singleton partagées (événements sans état).
 *
 * Permet de poster un const IEvent* dans une file FreeRTOS sans allocation
 * dynamique.
 */
namespace events
{
extern const InitEvent kInit;
extern const StartEvent kStart;
extern const StopEvent kStop;
} // namespace events
