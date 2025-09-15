all:discovery registry
discovery : discovery.cpp echo.pb.cc
	g++  -std=c++17 $^ -o  $@ -lspdlog -lfmt -lgflags -letcd-cpp-api -lcpprest -lbrpc -lssl -lcrypto -lprotobuf -lleveldb
registry : registry.cpp echo.pb.cc
	g++  -std=c++17 $^ -o  $@ -lspdlog -lfmt -lgflags -letcd-cpp-api -lcpprest -lbrpc -lssl -lcrypto -lprotobuf -lleveldb