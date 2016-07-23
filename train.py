# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import scipy

import time
import string
import datetime
import pickle

from nltk.tokenize.casual import TweetTokenizer
from nltk.corpus import stopwords

import pymorphy2

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import SGDClassifier
from sklearn import naive_bayes
from sklearn import svm

def remove_retweet(msg):
    return ' '.join(filter(lambda x:x[0]!='@' and not x.startswith('http'), msg.split()))

morph = pymorphy2.MorphAnalyzer()
def normal_form(word, remove_hashtag = False):
    if remove_hashtag and word.startswith('#'):
        word = word[1:]
        
    return morph.parse(word)[0].normal_form

#почему-то нет некоторых знаков пунктуации и части стоп-слов
custom_stops = [u'...', u'ещё', u'это', u'весь', u'..', u'—', u'я', u'и', u'a', u'\u2026']
stops = set(stopwords.words('russian') + list(string.punctuation) + custom_stops + list(string.digits))
def remove_stop_words(words):
    return [w for w in words if w not in stop]

tknzr = TweetTokenizer()
def tweet_tokenize(msg):
    return tknzr.tokenize(msg)

def convert_date(timestamp):
    if type(timestamp) is datetime.datetime:
        date = timestamp    
    else:
        date = datetime.datetime.fromtimestamp(timestamp)

    h = date.hour
    
    if h >= 23 or h <= 5:
        d_type = 0 #Night
    elif h > 5 and h <= 11:
        d_type = 1 #Morning
    elif h > 11 and h <= 18:
        d_type = 2 #Midday
    else:
        d_type = 3 #Evening
    
    return pd.Series({'Weekday':date.weekday(), 'DayPart': d_type})

if __name__ == '__main__':
    neg = pd.read_csv('data/train/negative.csv', sep = ';')
    pos = pd.read_csv('data/train/positive.csv', sep = ';')

    X = pd.concat([pos, neg])

    X = X.drop(['id', 'tmane', 'trep', 'trtw', 'tfav',
       'tstcount', 'tfrien', 'listcount', 'Unnamed: 11', 'Unnamed: 12',
       'Unnamed: 13', 'Unnamed: 14', 'Unnamed: 15', 'Unnamed: 16',
       'Unnamed: 17', 'Unnamed: 18', 'Unnamed: 19', 'Unnamed: 20',
       'Unnamed: 21', 'Unnamed: 22'], axis = 1)    

    date_col = X['tdate'].apply(convert_date)

    enc = OneHotEncoder()
    date_col = enc.fit_transform(date_col)

    y = X['ttype']
    X_tweets = X['ttext'].apply(remove_retweet)

    vectorizer = TfidfVectorizer(min_df = 5, ngram_range = (1, 2),
                             stop_words = stops, tokenizer = tweet_tokenize)

    print '*** Vectorization started ***'
    start_time = time.time()

    X_tweets = vectorizer.fit_transform(X_tweets)
    X_tweets = scipy.sparse.hstack([X_tweets, date_col])

    print '*** Vectorization completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2)

    print '*** Fitting started ***'
    start_time = time.time()

    model = SGDClassifier(n_iter=50, loss='modified_huber')
    model.fit(X_tweets, y)

    print '*** Fitting completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2)

    print '*** Dumping midels ***'
    start_time = time.time()

    with open('models/model_sgd.pkl', 'wb') as f:
        pickle.dump(model, f)

    with open('models/vectrorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)

    with open('models/one_hot.pkl', 'wb') as f:
        pickle.dump(enc, f)

    print '*** Dumping completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2)

