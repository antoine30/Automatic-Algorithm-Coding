/**
 * @file main.cpp
 * @brief Point d'entrée applicatif (STM32F4 + FreeRTOS).
 *
 * Initialise le HAL puis délègue au Scheduler : création des tâches, envoi des
 * événements d'initialisation, et démarrage de l'ordonnanceur.
 */

#include "stm32f4xx_hal.h"

#include "config/scheduler.h"

int main(void)
{
    // Initialisation matérielle (horloges, périphériques) — fournie par le BSP.
    HAL_Init();

    Scheduler &scheduler = Scheduler::getInstance();
    scheduler.init();  // Crée les tâches et poste INIT/START.
    scheduler.start(); // Démarre l'ordonnanceur (ne retourne pas).

    // Atteint uniquement si l'ordonnanceur n'a pas pu démarrer.
    for (;;)
    {
    }
    return 0;
}
