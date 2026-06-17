#pragma once

/**
 * @file TaskCommunication.h
 * @brief LLR_TSK_002 — Tâche de communication UART, pilotée par événements.
 *
 * Réagit aux événements INIT / START / STOP via des handlers virtuels (aucun
 * switch). La donnée reçue est traitée dans onStart() (déclenché par l'ISR RX).
 */

#include <cstddef>
#include <cstdint>

#include "interfaces/IDriver.h"
#include "tasks/TaskBase.h"

class TaskCommunication : public TaskBase
{
public:
    /// @param uartDriver Driver UART injecté par référence (injection de dépendance).
    explicit TaskCommunication(IDriver &uartDriver);

    // Handlers d'événements (appelés par IEvent::execute, double-dispatch).
    TaskStatus onInit() override;  ///< INIT  : init UART, vérifie la connexion.
    TaskStatus onStart() override; ///< START : lit l'UART + processMessage().
    TaskStatus onStop() override;  ///< STOP  : vide le buffer, log d'arrêt.
    const char *getName() const override;

private:
    IDriver &m_uart;
    static uint8_t s_rxBuffer[256]; ///< Buffer statique — no malloc.
    uint32_t m_rxCount;
    bool m_running;

    /// Traite un message reçu. @return OK si traité, ERROR si rejeté.
    TaskStatus processMessage(const uint8_t *buf, size_t len);
};
