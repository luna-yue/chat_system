.PHONYY:all
all:sync async main
sync:sync.cpp
	g++ $^ -o $@ -std=c++17  -lspdlog -lfmt
async:async.cpp
	g++ $^ -o $@ -std=c++17 -lspdlog -lfmt
main:main.cpp
	g++ $^ -o $@ -std=c++17 -lspdlog -lfmt -lgflags