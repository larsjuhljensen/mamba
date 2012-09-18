#CC     = g++
CC     = gcc
CFLAGS = -g -fpic -Wall -O3
LFLAGS = -fpic -shared -lboost_regex
PYTHON = -I/usr/include/python

all: ranker.py _ranker.so

clean:
	rm -f *_wrap.cxx *.o *.so *.pyc ranker.py

ranker.py ranker_wrap.cxx: ranker.i
	swig -python -c++ -threads $<

ranker.o: ranker.cxx ranker.h
	$(CC) $(CFLAGS) -c $<

ranker_wrap.o: ranker_wrap.cxx
	$(CC) $(CFLAGS) $(PYTHON) -c $<

_ranker.so: ranker.o ranker_wrap.o
	$(CC) $(LFLAGS) -o $@ $^
