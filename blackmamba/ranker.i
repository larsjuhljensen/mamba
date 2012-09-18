%module ranker

%typemap(in) vector< int > {
        unsigned int size = PyList_Size($input);
        for (unsigned int i = 0; i < size; i++) {
                $1.push_back(PyInt_AsLong(PyList_GetItem($input, i)));
        }
}

%typemap(freearg) vector< int > {
        //delete $1;
}

%typemap(out) vector< int > {
        PyObject* documents = PyList_New((int)$1.size());
        for (unsigned int i = 0; i < $1.size(); i++) {
                PyList_SetItem(documents, i, PyInt_FromLong((long) $1.at(i)));
                }
        $result = documents;
}

%include "ranker.h"

%{
        #include "ranker.h"
        #include <vector>
        using namespace std;
%}
