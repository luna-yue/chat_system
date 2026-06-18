CXX = g++

CXXFLAGS = -std=c++17 -O2 -pthread

PROTO_SRCS = \
	base.pb.cc \
	user.pb.cc \
	message.pb.cc \
	transmite.pb.cc	

TARGET = msg_test

all: $(TARGET)

$(TARGET): main.cpp $(PROTO_SRCS)
	$(CXX) $(CXXFLAGS) \
	main.cpp \
	$(PROTO_SRCS) \
	-lprotobuf \
	-o $(TARGET)

clean:
	rm -f $(TARGET)