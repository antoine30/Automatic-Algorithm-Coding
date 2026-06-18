# Host unit tests for the fixed-point RF pipeline (pure integer math — no HW).
#
# Usage:  make        build and run all suites
#         make clean  remove artifacts

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -I ../src
SRC       = ../src/algorithms

PHASE_SRC = test_phase_compute.cpp      $(SRC)/PhaseCompute.cpp
BESS_SRC  = test_bessel_spur_removal.cpp $(SRC)/BesselSpurRemoval.cpp
UNW_SRC   = test_phase_unwrapper.cpp    $(SRC)/PhaseUnwrapper.cpp
PROMO_SRC = test_adc_promote.cpp        $(SRC)/AdcPromote.cpp
SNR_SRC   = test_phase_snr.cpp          $(SRC)/PhaseCompute.cpp
PIPE_SRC  = test_rf_pipeline.cpp $(SRC)/RfPipeline.cpp $(SRC)/AdcPromote.cpp $(SRC)/BesselSpurRemoval.cpp $(SRC)/PhaseCompute.cpp $(SRC)/PhaseUnwrapper.cpp

.PHONY: all test clean

all: test

run_promote:  $(PROMO_SRC) ; $(CXX) $(CXXFLAGS) $(PROMO_SRC) -o run_promote
run_phase:    $(PHASE_SRC) ; $(CXX) $(CXXFLAGS) $(PHASE_SRC) -o run_phase
run_bessel:   $(BESS_SRC)  ; $(CXX) $(CXXFLAGS) $(BESS_SRC)  -o run_bessel
run_unwrap:   $(UNW_SRC)   ; $(CXX) $(CXXFLAGS) $(UNW_SRC)   -o run_unwrap
run_snr:      $(SNR_SRC)   ; $(CXX) $(CXXFLAGS) $(SNR_SRC)   -o run_snr
run_pipeline: $(PIPE_SRC)  ; $(CXX) $(CXXFLAGS) $(PIPE_SRC)  -o run_pipeline

test: run_promote run_phase run_bessel run_unwrap run_snr run_pipeline
	./run_promote
	@echo ""
	./run_phase
	@echo ""
	./run_bessel
	@echo ""
	./run_unwrap
	@echo ""
	./run_snr
	@echo ""
	./run_pipeline

clean:
	rm -f run_promote run_phase run_bessel run_unwrap run_snr run_pipeline
