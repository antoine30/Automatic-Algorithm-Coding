/**
 * @file test_event_dispatch.cpp
 * @brief Tests unitaires du cœur event-driven (indépendant de FreeRTOS/HAL).
 *
 * Vérifie l'exigence centrale : un événement exécute le code associé via une
 * MÉTHODE VIRTUELLE (double-dispatch), sans aucun switch/case. On valide que
 * chaque événement appelle bien le handler correspondant et propage le statut.
 *
 * Build : voir Makefile (cible `make`).
 */

#include "interfaces/IEvent.h"
#include "interfaces/ITask.h"

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

/// Tâche factice : compte les appels de chaque handler et renvoie un statut piloté.
class MockTask : public ITask
{
public:
    int initCalls = 0;
    int startCalls = 0;
    int stopCalls = 0;
    TaskStatus nextStatus = TaskStatus::OK;

    TaskStatus onInit() override
    {
        ++initCalls;
        return nextStatus;
    }
    TaskStatus onStart() override
    {
        ++startCalls;
        return nextStatus;
    }
    TaskStatus onStop() override
    {
        ++stopCalls;
        return nextStatus;
    }
    const char *getName() const override { return "MockTask"; }
};

static void test_init_event_routes_to_oninit()
{
    MockTask task;
    CHECK(events::kInit.execute(task) == TaskStatus::OK);
    CHECK(task.initCalls == 1);
    CHECK(task.startCalls == 0 && task.stopCalls == 0);
    CHECK(events::kInit.id() == EventId::INIT);
}

static void test_start_event_routes_to_onstart()
{
    MockTask task;
    CHECK(events::kStart.execute(task) == TaskStatus::OK);
    CHECK(task.startCalls == 1);
    CHECK(task.initCalls == 0 && task.stopCalls == 0);
    CHECK(events::kStart.id() == EventId::START);
}

static void test_stop_event_routes_to_onstop()
{
    MockTask task;
    CHECK(events::kStop.execute(task) == TaskStatus::OK);
    CHECK(task.stopCalls == 1);
    CHECK(task.initCalls == 0 && task.startCalls == 0);
    CHECK(events::kStop.id() == EventId::STOP);
}

static void test_status_is_propagated()
{
    MockTask task;
    task.nextStatus = TaskStatus::ERROR;
    CHECK(events::kInit.execute(task) == TaskStatus::ERROR);
    task.nextStatus = TaskStatus::NOT_INITIALIZED;
    CHECK(events::kStart.execute(task) == TaskStatus::NOT_INITIALIZED);
}

static void test_polymorphic_dispatch_via_base_pointer()
{
    // Dispatch via IEvent& : c'est le type dynamique qui choisit le handler,
    // sans aucun switch/case côté appelant.
    MockTask task;
    const IEvent *sequence[] = {&events::kInit, &events::kStart, &events::kStop};
    for (const IEvent *ev : sequence)
    {
        CHECK(ev->execute(task) == TaskStatus::OK);
    }
    CHECK(task.initCalls == 1);
    CHECK(task.startCalls == 1);
    CHECK(task.stopCalls == 1);
}

int main()
{
    std::printf("Running event-dispatch unit tests...\n");

    test_init_event_routes_to_oninit();
    test_start_event_routes_to_onstart();
    test_stop_event_routes_to_onstop();
    test_status_is_propagated();
    test_polymorphic_dispatch_via_base_pointer();

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
