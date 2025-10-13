all : publish consume
publish : publish.cpp
	g++ -g -std=c++17 $^ -o $@ -lamqpcpp -lev -lfmt -lspdlog -lgflags
consume : consume.cpp
	g++ -g -std=c++17 $^ -o $@ -lamqpcpp -lev -lfmt -lspdlog -lgflags