main : main.cpp chat_session_member-odb.cxx user-odb.cxx
	c++ -std=c++17 $^ -o $@ -I../../../odb/ -I./  -lodb-mysql -lodb -lodb-boost -lfmt -lspdlog -lgflags
