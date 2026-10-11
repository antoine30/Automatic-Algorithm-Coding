# Build and run the C++ mirror of the verified Lean Solution.
#
#   make           build + run the tests (uses the committed lean_generated.hpp)
#   make generate  regenerate lean_generated.hpp FROM Lean (needs the toolchain)
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra
BIN       = run_tests

.PHONY: all test generate clean
all: test

$(BIN): test_solution.cpp solution.hpp lean_generated.hpp
	$(CXX) $(CXXFLAGS) test_solution.cpp -o $(BIN)

test: $(BIN)
	./$(BIN)

# Re-emit lean_generated.hpp from the proved Lean Solution (Lean = oracle).
generate:
	cd .. && PATH="$$HOME/.elan/bin:$$PATH" lake build Solution >/dev/null \
	       && PATH="$$HOME/.elan/bin:$$PATH" lake env lean --run gen/Gen.lean

clean:
	rm -f $(BIN)
