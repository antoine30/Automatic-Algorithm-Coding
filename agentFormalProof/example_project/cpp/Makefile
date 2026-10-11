# Build and run the C++ mirror of the verified Lean Solution.
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra
BIN       = run_tests

.PHONY: all test clean
all: test

$(BIN): test_solution.cpp solution.hpp
	$(CXX) $(CXXFLAGS) test_solution.cpp -o $(BIN)

test: $(BIN)
	./$(BIN)

clean:
	rm -f $(BIN)
