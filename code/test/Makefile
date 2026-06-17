# Host unit tests (HAL/FreeRTOS-free for the core, + shim for TaskBase).
#
#  run_tests          : event dispatch (interfaces + IEvent), pure C++17.
#  run_tests_taskbase : TaskBase event loop via the FreeRTOS shim.
#
# The hardware drivers/config/tasks target STM32F4 + HAL and are built with
# the embedded toolchain (not covered here).
#
# Usage : make        -> build and run both suites
#         make clean  -> remove the artifacts

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra

CORE_SRC  = test_event_dispatch.cpp ../src/interfaces/IEvent.cpp
CORE_BIN  = run_tests

TB_SRC    = test_task_base.cpp ../src/tasks/TaskBase.cpp ../src/interfaces/IEvent.cpp
TB_BIN    = run_tests_taskbase

TS_SRC    = test_task_sensor.cpp ../src/tasks/TaskSensor.cpp ../src/tasks/TaskBase.cpp ../src/interfaces/IEvent.cpp
TS_BIN    = run_tests_sensor

DRV_SRC   = test_drivers.cpp ../src/drivers/UartDriver.cpp ../src/drivers/SpiDriver.cpp ../src/drivers/I2cDriver.cpp
DRV_BIN   = run_tests_drivers

.PHONY: all test clean

all: test

$(CORE_BIN): $(CORE_SRC)
	$(CXX) $(CXXFLAGS) -I ../src $(CORE_SRC) -o $(CORE_BIN)

# The shim must take precedence over the real headers: -I shim before -I ../src.
$(TB_BIN): $(TB_SRC)
	$(CXX) $(CXXFLAGS) -I shim -I ../src $(TB_SRC) -o $(TB_BIN)

$(TS_BIN): $(TS_SRC)
	$(CXX) $(CXXFLAGS) -I shim -I ../src $(TS_SRC) -o $(TS_BIN)

$(DRV_BIN): $(DRV_SRC)
	$(CXX) $(CXXFLAGS) -I shim -I ../src $(DRV_SRC) -o $(DRV_BIN)

test: $(CORE_BIN) $(TB_BIN) $(TS_BIN) $(DRV_BIN)
	./$(CORE_BIN)
	@echo ""
	./$(TB_BIN)
	@echo ""
	./$(TS_BIN)
	@echo ""
	./$(DRV_BIN)

clean:
	rm -f $(CORE_BIN) $(TB_BIN) $(TS_BIN) $(DRV_BIN)
