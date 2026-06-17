/**
 * @file TaskCommunication.cpp
 * @brief LLR_TSK_002 — Implémentation de la tâche de communication.
 */

#include "tasks/TaskCommunication.h"

// Le driver concret expose read(buf,len,timeout) ; on caste depuis IDriver.
#include "drivers/UartDriver.h"

uint8_t TaskCommunication::s_rxBuffer[256] = {0};

namespace
{
constexpr uint32_t kReadTimeoutMs = 1000; ///< Timeout de lecture UART (1 s).
constexpr UBaseType_t kPriority = 3;
constexpr uint32_t kStackWords = 512;
} // namespace

TaskCommunication::TaskCommunication(IDriver &uartDriver)
    : TaskBase("TaskComm", kStackWords, kPriority), m_uart(uartDriver),
      m_rxCount(0), m_running(false)
{
}

const char *TaskCommunication::getName() const
{
    return "TaskComm";
}

TaskStatus TaskCommunication::onInit()
{
    // Initialise le driver et vérifie la connexion.
    if (m_uart.init() != DriverStatus::OK)
    {
        return TaskStatus::ERROR;
    }
    if (!m_uart.isReady())
    {
        return TaskStatus::NOT_INITIALIZED;
    }
    m_running = false;
    m_rxCount = 0;
    return TaskStatus::OK;
}

TaskStatus TaskCommunication::onStart()
{
    if (!m_uart.isReady())
    {
        return TaskStatus::NOT_INITIALIZED; // START avant INIT.
    }
    m_running = true;

    // Lecture avec timeout de 1000 ms (le driver UART expose read()).
    auto *uart = static_cast<UartDriver *>(&m_uart);
    DriverStatus st = uart->read(s_rxBuffer, sizeof(s_rxBuffer), kReadTimeoutMs);

    if (st == DriverStatus::TIMEOUT)
    {
        // Le timeout n'arrête pas la tâche : on log et on continue.
        return TaskStatus::OK;
    }
    if (st == DriverStatus::ERROR)
    {
        // Erreur : reset du driver puis on continue.
        m_uart.reset();
        return TaskStatus::OK;
    }

    // Donnée reçue : traitement.
    ++m_rxCount;
    if (processMessage(s_rxBuffer, sizeof(s_rxBuffer)) != TaskStatus::OK)
    {
        // Message invalide : on l'ignore (log + discard).
        return TaskStatus::OK;
    }
    return TaskStatus::OK;
}

TaskStatus TaskCommunication::onStop()
{
    if (!m_uart.isReady())
    {
        return TaskStatus::NOT_INITIALIZED;
    }
    m_running = false;
    // Vide le buffer logiciel et journalise l'arrêt.
    for (size_t i = 0; i < sizeof(s_rxBuffer); ++i)
    {
        s_rxBuffer[i] = 0;
    }
    return TaskStatus::OK;
}

TaskStatus TaskCommunication::processMessage(const uint8_t *buf, size_t len)
{
    if (buf == nullptr || len == 0)
    {
        return TaskStatus::ERROR;
    }
    // TODO projet : décoder la trame applicative et émettre la réponse.
    return TaskStatus::OK;
}
