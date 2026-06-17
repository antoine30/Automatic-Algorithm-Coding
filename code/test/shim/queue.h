#pragma once

/**
 * @file queue.h (SHIM)
 * @brief File FreeRTOS simulée (FIFO) — tests hôte uniquement.
 *
 * Implémentation simple à base de std::deque. xQueueReceive est NON bloquant
 * (retourne pdFALSE si vide) pour ne pas figer les tests.
 */

#include "FreeRTOS.h"

#include <cstring>
#include <deque>
#include <vector>

struct QueueDef
{
    UBaseType_t itemSize;
    UBaseType_t maxLen;
    std::deque<std::vector<uint8_t>> items;
};

typedef QueueDef *QueueHandle_t;

inline QueueHandle_t xQueueCreate(UBaseType_t length, UBaseType_t itemSize)
{
    QueueDef *q = new QueueDef();
    q->itemSize = itemSize;
    q->maxLen = length;
    return q;
}

inline void vQueueDelete(QueueHandle_t q) { delete q; }

inline BaseType_t xQueueSend(QueueHandle_t q, const void *item, TickType_t)
{
    if (q == nullptr || q->items.size() >= q->maxLen)
    {
        return pdFALSE;
    }
    std::vector<uint8_t> cell(q->itemSize);
    std::memcpy(cell.data(), item, q->itemSize);
    q->items.push_back(std::move(cell));
    return pdPASS;
}

inline BaseType_t xQueueSendFromISR(QueueHandle_t q, const void *item,
                                    BaseType_t *higherPriorityTaskWoken)
{
    if (higherPriorityTaskWoken != nullptr)
    {
        *higherPriorityTaskWoken = pdFALSE;
    }
    return xQueueSend(q, item, 0);
}

inline BaseType_t xQueueReceive(QueueHandle_t q, void *dst, TickType_t)
{
    if (q == nullptr || q->items.empty())
    {
        return pdFALSE; // Non bloquant côté shim.
    }
    std::memcpy(dst, q->items.front().data(), q->itemSize);
    q->items.pop_front();
    return pdTRUE;
}
