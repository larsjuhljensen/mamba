#ifndef __RANKER_HEADER__
#define __RANKER_HEADER__

#include "ranker_nonswig.h"

class score_item;

class Ranker
{
	private:
		INT_INT_VECTOR_MAP background_entity_doc_map;
		INT_INT_VECTOR_MAP background_doc_entity_map;
		const char * benchmark_file;

	private:
		INT_INT_MAP* count_entities(vector< int > docs);

	public:
		INT_DOUBLE_MAP* score_entities(vector< int > q, vector< int > p, vector< int > n, float alpha);
		vector<score_item>* score_documents(vector< int > q, vector< int > p, vector< int > n, float alpha);
		vector< int > rank_documents(vector< int > q, vector< int > p, vector< int > n, float alpha);
		void read_mentions(char const * filename);
};

#endif
