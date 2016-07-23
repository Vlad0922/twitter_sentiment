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
import datetime
import time

tknzr = TweetTokenizer()
def tweet_tokenize(msg):
    return tknzr.tokenize(msg)

def remove_retweet(msg):
    return ' '.join(filter(lambda x:x[0]!='@' and not x.startswith('http'), msg.split()))

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

def preprocess_tweet(text, date):
        text = vectorizer.transform([remove_retweet(text)])
        date = enc.transform([convert_date(date)])

        return scipy.sparse.hstack([text, date])

SENTIMENT_THRESHOLD = 0.8
def predict_sentiment(text, date):
    msg = preprocess_tweet(text, date)
    proba = model.predict_proba(msg)[0]

    if proba[0] >= SENTIMENT_THRESHOLD:
        return 'neg'
    elif proba[1] >= SENTIMENT_THRESHOLD:
        return 'pos'
    else:
        return 'neutral'

class MyStreamListener(tweepy.streaming.StreamListener):
    def on_status(self, status):
        sentiment = predict_sentiment(status.text, status.created_at)
        print sentiment, '|', status.text

#пока только русский язык т.к. классификатор обучен только на русских твитах
#TODO: английский язык
keywords = [u'МФТИ', u'физтех']

if __name__ == '__main__':
    start_time = time.time()
    print '*** Loading started ***'

    with open('models/model_sgd.pkl', 'rb') as f:
        model = pickle.load(f)

    with open('models/vectrorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)

    with open('models/one_hot.pkl', 'rb') as f:
        enc = pickle.load(f)

    print '*** Loading completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2)

    with open('tokens.txt') as f:
        (access_token, access_token_secret,
            consumer_key, consumer_secret) = f.read().split()

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    print '*** Stream started ***'

    myStream = tweepy.Stream(auth = auth, listener = MyStreamListener())
    myStream.filter(track = keywords)

