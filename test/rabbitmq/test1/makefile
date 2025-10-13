all : publish consume
publish : publish.cpp
	g++ -std=c++17 $^ -o $@ -lamqpcpp -lev
consume : consume.cpp
	g++ -std=c++17 $^ -o $@ -lamqpcpp -lev