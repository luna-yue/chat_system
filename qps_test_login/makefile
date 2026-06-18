CXX = g++

TARGET = qps_test

SRCS = main.cpp \
       base.pb.cc \
       user.pb.cc \
       file.pb.cc

OBJS = $(SRCS:.cc=.o)
OBJS := $(OBJS:.cpp=.o)

CXXFLAGS = -std=c++17 -O2

LIBS = -lprotobuf -lpthread

$(TARGET): $(OBJS)
	$(CXX) -o $@ $^ $(LIBS)

%.o: %.cc
	$(CXX) $(CXXFLAGS) -c $< -o $@

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f *.o $(TARGET)