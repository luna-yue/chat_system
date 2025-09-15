all : server client
server : svr.cpp echo.pb.cc
	g++ -std=c++17 $^ -o $@ -lbrpc -lgflags -lssl -lcrypto -lprotobuf -lleveldb -lspdlog -lfmt -lgflags
client : cli.cpp echo.pb.cc
	g++ -std=c++17 $^ -o $@ -lbrpc -lgflags -lssl -lcrypto -lprotobuf -lleveldb -lspdlog -lfmt -lgflags