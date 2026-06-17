/**
 * @file test_task_sensor.cpp
 * @brief Tests hôte de TaskSensor avec un mock ISensor (shim FreeRTOS).
 */

#include "tasks/TaskSensor.h"

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

/// Capteur factice pilotable pour les tests.
class MockSensor : public ISensor
{
public:
    DriverStatus initStatus = DriverStatus::OK;
    DriverStatus calibStatus = DriverStatus::OK;
    DriverStatus readStatus = DriverStatus::OK;
    bool ready = false;
    bool calibrated = false;
    int readCalls = 0;

    DriverStatus init() override
    {
        ready = (initStatus == DriverStatus::OK);
        return initStatus;
    }
    DriverStatus reset() override { return DriverStatus::OK; }
    bool isReady() const override { return ready; }
    const char *getName() const override { return "MockSensor"; }

    DriverStatus read(uint8_t *buf, size_t len) override
    {
        ++readCalls;
        if (buf != nullptr && len > 0 && readStatus == DriverStatus::OK)
        {
            buf[0] = 0x42;
        }
        return readStatus;
    }
    DriverStatus calibrate() override
    {
        calibrated = (calibStatus == DriverStatus::OK);
        return calibStatus;
    }
    bool isCalibrated() const override { return calibrated; }
};

static void test_init_calibrates_sensor()
{
    MockSensor sensor;
    TaskSensor task(sensor);
    CHECK(task.onInit() == TaskStatus::OK);
    CHECK(sensor.isReady());
    CHECK(sensor.isCalibrated());
}

static void test_start_before_init_fails()
{
    MockSensor sensor;
    TaskSensor task(sensor);
    CHECK(task.onStart() == TaskStatus::NOT_INITIALIZED);
    CHECK(task.sampleCount() == 0u);
}

static void test_nominal_acquisition()
{
    MockSensor sensor;
    TaskSensor task(sensor);
    CHECK(task.onInit() == TaskStatus::OK);
    CHECK(task.onStart() == TaskStatus::OK);
    CHECK(task.onStart() == TaskStatus::OK);
    CHECK(task.sampleCount() == 2u);
    CHECK(sensor.readCalls == 2);
}

static void test_read_timeout_does_not_stop()
{
    MockSensor sensor;
    TaskSensor task(sensor);
    task.onInit();
    sensor.readStatus = DriverStatus::TIMEOUT;
    CHECK(task.onStart() == TaskStatus::OK); // timeout toléré
    CHECK(task.sampleCount() == 0u);         // pas d'échantillon compté
}

static void test_post_event_uses_queue()
{
    // Le chemin file + dispatch virtuel est couvert par test_task_base.cpp ;
    // ici on vérifie juste que TaskSensor accepte de poster ses événements.
    MockSensor sensor;
    TaskSensor task(sensor);
    task.start();
    CHECK(task.postEvent(events::kInit) == true);
    CHECK(task.postEvent(events::kStart) == true);
}

int main()
{
    std::printf("Running TaskSensor unit tests (mock ISensor)...\n");

    test_init_calibrates_sensor();
    test_start_before_init_fails();
    test_nominal_acquisition();
    test_read_timeout_does_not_stop();
    test_post_event_uses_queue();

    std::printf("\n%d checks, %d failure(s)\n", g_checks, g_failures);
    if (g_failures == 0)
    {
        std::printf("ALL TESTS PASSED\n");
        return 0;
    }
    std::printf("TESTS FAILED\n");
    return 1;
}
