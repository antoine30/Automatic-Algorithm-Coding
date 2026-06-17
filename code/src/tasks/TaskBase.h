#pragma once

/**
 * @file TaskBase.h
 * @brief LLR_TSK_001 — Classe de base abstraite des tâches FreeRTOS.
 *
 * Gère le cycle de vie FreeRTOS et une FILE D'ÉVÉNEMENTS. La boucle de tâche
 * bloque sur la file, reçoit un IEvent, et appelle event.execute(*this) qui
 * route vers le handler virtuel adéquat (onInit/onStart/onStop).
 * AUCUN switch/case sur le type d'événement : le dispatch est polymorphe.
 */

#include <cstdint>

#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"

#include "interfaces/IEvent.h"
#include "interfaces/ITask.h"

class TaskBase : public ITask
{
public:
    TaskBase(const char *name, uint32_t stackSize, UBaseType_t priority,
             uint32_t queueLength = 8);
    virtual ~TaskBase();

    void start(); ///< Crée la file d'événements et démarre la tâche FreeRTOS.
    void stop();  ///< Supprime la tâche FreeRTOS et la file.

    /// Poste un événement (contexte tâche). @return false si la file est pleine.
    bool postEvent(const IEvent &event, TickType_t timeout = 0);

    /// Poste un événement depuis une ISR.
    bool postEventFromISR(const IEvent &event, BaseType_t *higherPriorityTaskWoken);

protected:
    /// Reçoit un événement (avec @p timeout) et le dispatche par méthode
    /// virtuelle (event->execute). @return true si un événement a été traité.
    /// Extrait de la boucle pour être testable hors ordonnanceur.
    bool processNextEvent(TickType_t timeout);

    const char *m_name;
    uint32_t m_stackSize;
    UBaseType_t m_priority;
    uint32_t m_queueLength;
    TaskHandle_t m_handle;
    QueueHandle_t m_eventQueue; ///< Transporte des const IEvent* (no malloc).

private:
    static void taskEntry(void *param); ///< Point d'entrée FreeRTOS (statique).
    void run();                         ///< Boucle réception + dispatch.
};
