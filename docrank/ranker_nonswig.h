#ifndef __RANKER_NONSWIG_HEADER__
#define __RANKER_NONSWIG_HEADER__

#include <vector>
#include <tr1/unordered_map>

using namespace std;
using namespace tr1;

typedef vector<int> INT_VECTOR;
typedef unordered_map<int, INT_VECTOR> INT_INT_VECTOR_MAP;
typedef unordered_map<int, float> INT_DOUBLE_MAP;
typedef unordered_map<int, int> INT_INT_MAP;

#endif
