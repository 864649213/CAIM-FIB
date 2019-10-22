"""
.. module:: TFIDFViewer

TFIDFViewer
******

:Description: TFIDFViewer

    Receives two paths of files to compare (the paths have to be the ones used when indexing the files)

:Authors:
    bejar

:Version: 

:Date:  05/07/2017
"""

from __future__ import print_function, division
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from elasticsearch.client import CatClient
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Q

import argparse

import numpy as np

__author__ = 'bejar'

def search_file_by_path(client, index, path):
    """
    Search for a file using its path

    :param path:
    :return:
        """
    s = Search(using=client, index=index)
    q = Q('match', path=path)  # exact search in the path field
    s = s.query(q)
    result = s.execute()

    lfiles = [r for r in result]
    if len(lfiles) == 0:
        raise NameError(f'File [{path}] not found')
    else:
        return lfiles[0].meta.id


def document_term_vector(client, index, id):
    """
    Returns the term vector of a document and its statistics a two sorted list of pairs (word, count)
    The first one is the frequency of the term in the document, the second one is the number of documents
    that contain the term

    :param client:
    :param index:
    :param id:
    :return:
    """
    termvector = client.termvectors(index=index, id=id, fields=['text'],
                                    positions=False, term_statistics=True)

    file_td = {}
    file_df = {}

    if 'text' in termvector['term_vectors']:
        for t in termvector['term_vectors']['text']['terms']:
            file_td[t] = termvector['term_vectors']['text']['terms'][t]['term_freq']
            file_df[t] = termvector['term_vectors']['text']['terms'][t]['doc_freq']
    return sorted(file_td.items()), sorted(file_df.items())


def toTFIDF(client, index, file_id):
    """
    Returns the term weights of a document

    :param file:
    :return:
    """

    # Get document terms frequency and overall terms document frequency
    file_tv, file_df = document_term_vector(client, index, file_id)

    max_freq = max([f for _, f in file_tv])

    dcount = doc_count(client, index)


    tfidfw = []
    for (t, w),(_, df) in zip(file_tv, file_df):
        tf = w/max_freq
        idf = np.log2(dcount/df)
        tfidfw.append((t, tf*idf))


    return normalize(tfidfw)

def print_term_weigth_vector(twv):
    """
    Prints the term vector and the correspondig weights
    :param twv:
    :return:
    """

    for (t, x) in twv:
        print(t)
        print(x)


def normalize(tw):
    """
    Normalizes the weights in t so that they form a unit-length vector
    It is assumed that not all weights are 0
    :param tw:
    :return:
    """
    #
    tw_1 = [ i for i, j in tw ]
    tw_2 = [ j for i, j in tw ]
    modulo = np.sqrt(np.sum(np.square(tw_2)))
    tw_2 = np.divide(tw_2, modulo)
    tw = list(zip(tw_1, tw_2))
    #
    return tw


def cosine_similarity(tw1, tw2):
    """
    Computes the cosine similarity between two weight vectors, terms are alphabetically ordered
    :param tw1:
    :param tw2:
    :return:
    """
    #
    tw1_2 = [j for i, j in tw1]
    modulo1 = np.sqrt(np.sum(np.square(tw1_2)))
    tw2_2 = [j for i, j in tw2]
    modulo2 = np.sqrt(np.sum(np.square(tw2_2)))
    total = 0
   
    count1 = 0
    count2 = 0
    
    while(count1 < len(tw1) and count2 < len(tw2)):
        
        if(tw1[count1][0] == tw2[count2][0]):
            total = total+tw1[count1][1]*tw2[count2][1]
            count1 = count1+1
            count2 = count2+1
            
        elif(tw1[count1][0] < tw2[count2][0]):
            count1 = count1+1
        
        else:
            count2 = count2+1
        
    return total/(modulo1*modulo2)
	

def doc_count(client, index):
    """
    Returns the number of documents in an index

    :param client:
    :param index:
    :return:
    """
    return int(CatClient(client).count(index=[index], format='json')[0]['count'])


def experiment(index, files, prnt=False):

    file1 = files[0]
    file2 = files[1]

    client = Elasticsearch()

    try:

        # Get the files ids
        file1_id = search_file_by_path(client, index, file1)
        file2_id = search_file_by_path(client, index, file2)

        # Compute the TF-IDF vectors
        file1_tw = toTFIDF(client, index, file1_id)
        file2_tw = toTFIDF(client, index, file2_id)

        if prnt:
            print(f'TFIDF FILE {file1}')
            print_term_weigth_vector(file1_tw)
            print ('---------------------')
            print(f'TFIDF FILE {file2}')
            print_term_weigth_vector(file2_tw)
            print ('---------------------')

        # print(f"Similarity = {cosine_similarity(file1_tw, file2_tw):3.5f}")
        return(cosine_similarity(file1_tw, file2_tw))

    except NotFoundError:
        print(f'Index {index} does not exists')

