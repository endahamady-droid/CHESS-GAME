CXX = g++
CXXFLAGS = -Wall -Wextra -Wpedantic -std=c++17

.PHONY: all clean

all: chess

chess: main.o board.o view.o mask.o game.o
	$(CXX) main.o board.o view.o mask.o game.o -o chess

main.o: main.cpp types.hpp board.hpp view.hpp mask.hpp
	$(CXX) $(CXXFLAGS) -c main.cpp

board.o: board.cpp board.hpp types.hpp
	$(CXX) $(CXXFLAGS) -c board.cpp

view.o: view.cpp view.hpp types.hpp mask.hpp
	$(CXX) $(CXXFLAGS) -c view.cpp

mask.o: mask.cpp mask.hpp types.hpp board.hpp
	$(CXX) $(CXXFLAGS) -c mask.cpp

game.o: game.cpp game.hpp mask.hpp types.hpp
	$(CXX) $(CXXFLAGS) -c game.cpp

clean:
	rm -f *.o chess
