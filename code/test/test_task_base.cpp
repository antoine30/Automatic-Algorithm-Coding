/**
 * @file test_task_base.cpp
 * @brief Tests hôte de TaskBase : file d'événements + dispatch virtuel.
 *
 * Utilise le shim FreeRTOS (test/shim) pour exécuter la vraie logique de
 * TaskBase (postEvent + processNextEvent) sans ordonnanceur ni matériel.
 */

#include "tasks/TaskBase.h"

#include "interfaces/IEvent.h"

#include <cstdio>

static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                            \
    do                                                                         \
    {                                                                          \
        ++g_checks;                                                            \
        if (!(cond))                                                           \
        {                                                                      \
            ++g_failures;                                                      \
            std::printf("  [FAIL] %s:%d  %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                      \
    } while (0)

/// Tâche concrète de test : compte les handlers et expose processNextEvent.
class TestTask : public TaskBase
{
public:
    TestTask() : TaskBase("TestTask", 128, 1, 8) {}

    int initCalls = 0;
    int startCalls = 0;
    int stopCalls = 0;

    TaskStatus onInit() override
    {
        ++initCalls;
        return TaskStatus::OK;
    }
    TaskStatus onStart() override
    {
        ++startCalls;
        return TaskStatus::OK;
    }
    TaskStatus onStop() override
    {
        ++stopCalls;
        return TaskStatus::OK;
    }
    const char *getName() const override { return "TestTask"; }

    // Expose le dispatch unitaire pour les tests.
    using TaskBase::processNextEvent;
};

static void test_post_then_dispatch_routes_correctly()
{
    TestTask task;
    task.start(); // crée la file (shim).

    CHECK(task.postEvent(events::kInit) == true);
    CHECK(task.postEvent(events::kStart) == true);
    CHECK(task.postEvent(events::kStop) == true);

    // Chaque dispatch consomme un événement et appelle le bon handler virtuel.
    CHECK(task.processNextEvent(0) == true);
    CHECK(task.initCalls == 1);
    CHECK(task.processNextEvent(0) == true);
    CHECK(task.startCalls == 1);
    CHECK(task.processNextEvent(0) == true);
    CHECK(task.stopCalls == 1);

    // File vide : plus rien à dispatcher.
    CHECK(task.processNextEvent(0) == false);
}

static void test_fifo_order_preserved()
{
    TestTask task;
    task.start();

    // Deux INIT puis un STOP : l'ordre FIFO doit être respecté.
    task.postEvent(events::kInit);
    task.postEvent(events::kInit);
    task.postEvent(events::kStop);

    CHECK(task.processNextEvent(0) && task.initCalls == 1 && task.stopCalls == 0);
    CHECK(task.processNextEvent(0) && task.initCalls == 2 && task.stopCalls == 0);
    CHECK(task.processNextEvent(0) && task.stopCalls == 1);
}

static void test_post_without_start_fails()
{
    TestTask task; // pas de start() → file non créée.
    CHECK(task.postEvent(events::kInit) == false);
    CHECK(task.processNextEvent(0) == false);
}

int main()
{
    std::printf("Running TaskBase unit tests (with FreeRTOS shim)...\n");

    test_post_then_dispatch_routes_correctly();
    test_fifo_order_preserved();
    test_post_without_start_fails();

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
