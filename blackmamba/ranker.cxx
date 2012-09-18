#include "ranker.h"
#include <algorithm>
#include <iostream>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>


class score_item
{
	public:
		int key;
		float value;

	public:
		score_item(int key, float value)
		{
			this->key = key;
			this->value = value;
		}
};

bool compare(const score_item& lhs, const score_item& rhs)
{	
	return lhs.value > rhs.value;
}


INT_INT_MAP* Ranker::count_entities(vector< int > documents) {
	INT_INT_MAP* counts = new INT_INT_MAP();
	for (vector< int >::iterator it1 = documents.begin(); it1 != documents.end(); it1++) {
		vector< int >& entities = this->background_doc_entity_map[*it1];
		for (vector< int >::iterator it2 = entities.begin(); it2 != entities.end(); it2++) {
			if (counts->find(*it2) == counts->end()) {
				counts->insert(make_pair< int, int >(*it2, 1));
			} else {
				(*counts)[*it2]++;
			}
		}
	}
	return counts;
}

INT_DOUBLE_MAP* Ranker::score_entities(vector< int > q, vector< int > p, vector< int > n, float alpha) {
	INT_DOUBLE_MAP* entity_scores = new INT_DOUBLE_MAP();
	
	INT_INT_MAP* qcounts = this->count_entities(q);
	INT_INT_MAP* pcounts = this->count_entities(p);
	INT_INT_MAP* ncounts = this->count_entities(n);
	
	int qsize = q.size();
	int psize = p.size();
	int nsize = n.size();
	int bsize = this->background_doc_entity_map.size();

	for (INT_INT_MAP::iterator qit = qcounts->begin(); qit != qcounts->end(); qit++) {
		INT_INT_VECTOR_MAP::iterator bit = this->background_entity_doc_map.find(qit->first);
		if (bit != this->background_entity_doc_map.end()) {
			int pcount = 0;
			INT_INT_MAP::iterator pit = pcounts->find(qit->first);
			if (pit != pcounts->end()) {
				pcount = pit->second;
			}
			int ncount = 0;
			INT_INT_MAP::iterator nit = ncounts->find(qit->first);
			if (nit != ncounts->end()) {
				ncount = nit->second;
			}
			float pos_frac = (pcount + alpha) / (psize + alpha*qsize/qit->second);
			float neg_frac = (ncount + alpha) / (nsize + alpha*bsize/bit->second.size());
			(*entity_scores)[qit->first] = log(pos_frac / neg_frac);
		} else {
			(*entity_scores)[qit->first] = 0;
		}
	}
	delete qcounts;
	delete pcounts;
	delete ncounts;
	return entity_scores;	
}

vector<score_item>* Ranker::score_documents(vector< int > q, vector< int > p, vector< int > n, float alpha) {
	vector<score_item>* document_scores = new vector<score_item>();
	INT_DOUBLE_MAP* entity_scores = this->score_entities(q, p, n, alpha);

	for (vector< int >::iterator qit = q.begin(); qit != q.end(); qit++) {
		vector< int >& entities = this->background_doc_entity_map[*qit];
		float score = 0.0;
		for (vector< int >::iterator it = entities.begin(); it != entities.end(); it++) {
			score += (*entity_scores)[*it];
		}
		document_scores->push_back(score_item(*qit, score));
	}
	delete entity_scores;
	return document_scores;
}

vector< int > Ranker::rank_documents(vector< int > q, vector< int > p, vector< int > n, float alpha) {
	vector<score_item>* document_scores = score_documents(q, p, n, alpha);
	sort(document_scores->begin(), document_scores->end(), compare);
	vector< int > documents;
	for (vector<score_item>::iterator it = document_scores->begin(); it != document_scores->end(); it++) {
		documents.push_back(it->key);
	}
	delete document_scores;
	return documents;
}

void Ranker::read_mentions(char const * filename) {

	FILE* file = fopen(filename, "r");
	if (!file) {
		cerr << "Could not open file" << endl;
	}
	cerr << "Reading file..." << endl;

	int entity = 1;
	int document = 0;
	int column = 0;
	while (!feof(file)) {
		char c = fgetc(file);
		if (column == 2) {
			if (c >= '0' && c <= '9') {
				document = 10 * document + c - '0';
			} else {

				INT_INT_VECTOR_MAP::iterator it =
				this->background_doc_entity_map.find(document);

				if (it == this->background_doc_entity_map.end()) {
					this->background_doc_entity_map[document] = INT_VECTOR();
					it = this->background_doc_entity_map.find(document);
				}
				it->second.push_back(entity);
				it = background_entity_doc_map.find(entity);
				if (it == background_entity_doc_map.end()) {
					this->background_entity_doc_map[entity] = INT_VECTOR();
					it = this->background_entity_doc_map.find(entity);
				}
				it->second.push_back(document);

				document = 0;
				if (c == '\n') {
					entity++;
					column = 0;

					if (entity % 1000 == 0)
					cerr << entity << "\r";

				}
			}
		} else {
			if (c == '\t') {
				column++;
			} else if (c == '\n') {
				entity++;
				column = 0;
			}
		}

	}
	fclose(file);
}
