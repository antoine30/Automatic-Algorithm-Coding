#pragma once

/**
 * @file TaskCommunication.h
 * @brief LLR_TSK_002 — Event-driven UART communication task.
 *
 * Reacts to INIT / START / STOP events via virtual handlers (no switch).
 * Received data is processed in onStart() (triggered by the RX ISR).
 */

#include <cstddef>
#include <cstdint>

#include "interfaces/IDriver.h"
#include "tasks/TaskBase.h"

class TaskCommunication : public TaskBase
{
public:
    /// @param uartDriver UART driver injected by reference (dependency injection).
    explicit TaskCommunication(IDriver &uartDriver);

    // Event handlers (called by IEvent::execute, double-dispatch).
    TaskStatus onInit() override;  ///< INIT  : init UART, check the connection.
    TaskStatus onStart() override; ///< START : read the UART + processMessage().
    TaskStatus onStop() override;  ///< STOP  : flush the buffer, log shutdown.
    const char *getName() const override;

private:
    IDriver &m_uart;
    static uint8_t s_rxBuffer[256]; ///< Static buffer — no malloc.
    uint32_t m_rxCount;
    bool m_running;

    /// Processes a received message. @return OK if processed, ERROR if rejected.
    TaskStatus processMessage(const uint8_t *buf, size_t len);
};
