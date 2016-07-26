# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

import scipy

import tweepy

from nltk.tokenize.casual import TweetTokenizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import OneHotEncoder

import pickle
import time
import codecs
import datetime

tknzr = TweetTokenizer()
def tweet_tokenize(msg):
    return tknzr.tokenize(msg)

def remove_retweet(msg):
    return ' '.join(filter(lambda x:x[0]!='@' and not x.startswith('http'), msg.split()))

def preprocess_tweet(text):
    return vectorizer.transform([remove_retweet(text)])

SENTIMENT_THRESHOLD = 0.7
def predict_sentiment(text):
    msg = preprocess_tweet(text)
    proba = model.predict_proba(msg)[0]

    if proba[0] >= SENTIMENT_THRESHOLD:
        return 'neg'
    elif proba[1] >= SENTIMENT_THRESHOLD:
        return 'pos'
    else:
        return 'neutral'

class MyStreamListener(tweepy.streaming.StreamListener):
    def on_status(self, status):
        sentiment = predict_sentiment(status.text)
        print sentiment, '|', status.text

        with codecs.open('data/stream/MIPT.csv', 'a', 'utf-8') as f:
            f.write('%s;%s;%s\n' % (str(status.created_at), status.text, sentiment))


#пока только русский язык т.к. классификатор обучен только на русских твитах
#TODO: английский язык
keywords = [u'МФТИ', u'физтех']

if __name__ == '__main__':
    start_time = time.time()
    print '*** Loading started ***'

    with open('models/model_sgd.pkl', 'rb') as f:
        model = pickle.load(f)

    with open('models/vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)

    print '*** Loading completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2)

    with open('tokens.txt') as f:
        (access_token, access_token_secret,
            consumer_key, consumer_secret) = f.read().split()

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    print '*** Stream started *** %s' % str(datetime.datetime.now().time())

    myStream = tweepy.Stream(auth = auth, listener = MyStreamListener())
    myStream.filter(track = keywords)

