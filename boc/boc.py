import logging
from collections import Counter, defaultdict
import math
import sys

from scipy.sparse import csr_matrix
import scipy.sparse
from sklearn.utils.extmath import safe_sparse_dot
from gensim.models import Word2Vec, KeyedVectors
from spherecluster import SphericalKMeans


class BOC():

    def __init__(self, input_path=None, embedding_dim=200, 
        context=8, min_freq=100, num_concept=100, iterations=5):
    	# Unified model & doc path
    	# Different embedding methods --> numpy ndarray
        if input_path is None:
            raise ValueError("Must specify either the document path or pre-trained word2vec path")
        
        if input_path[-3:]=="txt":
            self.doc_path=input_path
            self.mode_path=None
        else:
            self.doc_path=None
            self.model_path=input_path

        self.embedding_dim=embedding_dim
        self.context=context
        self.min_freq=min_freq
        self.num_concept=num_concept
        self.iterations=iterations

    
    def fit(self, w2v_saver=0, output_path=""):
        
        if self.model_path is not None:
            wv, idx2word=load_w2v(self.doc_path)
        else:
            wv, idx2word=train_w2v(self.doc_path, self.embedding_dim, 
                self.context, self.min_freq, self.iterations, w2v_saver)

        wv_cluster_id=_cluster_wv(wv, self.num_concept)
        bow=_create_bow(idx2word)
        w2c=_create_w2c(idx2word, wv_cluster_id)
        boc=_apply_cfidf(safe_sparse_dot(bow, w2c))
        
        if output_path:
           _save_boc(output_path, idx2word, wv_cluster_id)
            
        return boc, [wc_pair for wc_pair in zip(idx2word, wv_cluster_id)], idx2word


def _save_boc(filepath, idx2word, wv_cluster_id):
    scipy.sparse.save_npz(filepath+'.npz', boc)
    with open(filepath+'.txt', 'w') as f:
        for wc_pair in zip(idx2word, wv_cluster_id):
            f.write(str(wc_pair)+'\n')


def _cluster_wv(wv, num_concept):
    skm=SphericalKMeans(n_clusters=self.num_concept)
    skm.fit(wv)
    return skm.labels_


def _create_bow(idx2word):
    rows=[]
    cols=[]
    vals=[]
    word2idx={word:idx for idx, word in enumerate(idx2word)}
    with open(self.doc_path, "r") as f:
        for i, doc in enumerate(f):
            tokens=doc.rstrip().split(" ")
            tokens_count=Counter([word2idx[token] for token in tokens if token in word2idx])
            for idx, count in tokens_count.items():
                rows.append(i)
                cols.append(idx)
                vals.append(float(count))
    return csr_matrix((vals, (rows, cols)), shape=(i+1, len(word2idx)))


def _create_w2c(idx2word, cluster_label):
    if len(idx2word)!=len(cluster_label):
        raise IndexError("Dimensions between words and labels mismatched")

    rows=[i for i, idx2word in enumerate(idx2word)]
    cols=[j for j in cluster_label]
    vals=[1.0 for i in idx2word]

    return csr_matrix((vals, (rows, cols)), shape=(len(idx2word), self.num_concept))


def _apply_cfidf(csr_matrix):
    num_docs, num_concepts=csr_matrix.shape
    _, nz_concept_idx=csr_matrix.nonzero()
    cf=np.bincount(nz_concept, minlength=num_concepts)
    icf[np.isinf(icf)]=0
    icf=math.log10(num_docs / cf)
    return safe_sparse_dot(csr_matrix, scipy.sparse.diags(icf))


def tokenize(doc_path):
    with open(doc_path, "r") as f:
        for doc in f:
            yield doc.rstrip().split(" ")


def train_w2v(doc_path, embedding_dim, context, min_freq, iterations, save=0):
    tokenized_docs=tokenize(doc_path)
    model=Word2Vec(size=embedding_dim, window=context, min_count=min_freq, sg=1)
    model.build_vocab(tokenized_docs)
    model.train(tokenized_docs, total_examples=model.corpus_count, epochs=iterations)
    
    if (save==1):
        model_name="w2v_model_d%d_w%d" %(embedding_dim, context) 
        model.wv.save_word2vec_format(model_name)

    return model.wv.vectors, model.wv.index2word


def load_w2v(model_path):
    return KeyedVectors.load_word2vec_format(model_path)
