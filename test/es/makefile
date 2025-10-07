.PHONY: ALL
ALL: main testhpp
main : main.cpp
	g++ -std=c++17 $^ -o $@ -lcpr -lelasticlient
testhpp : testhpp.cpp
	g++ -std=c++17  $^ -o  $@ -lcpr -lelasticlient -lspdlog -lfmt -lgflags -ljsoncpp