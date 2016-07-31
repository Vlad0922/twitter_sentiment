# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import string
import scipy
import os

import json
import datetime
import time

from random import random

from collections import deque

from flask import Flask, render_template, make_response, request

import nltk
from nltk.tokenize.casual import TweetTokenizer
from nltk.corpus import stopwords

import tweepy
import threading

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer

import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier

app = Flask(__name__)

lock = threading.Lock()
last_tweets = deque()

NEG_TWEET = -1
POS_TWEET = 1

with open('tokens.txt') as f:
    (access_token, access_token_secret,
        consumer_key, consumer_secret) = f.read().split()

def date_distribution(X, date_from, date_to, step = 'day', step_count = 1, by_blocks = False):
    neg = X[X['ttype'] == NEG_TWEET]
    pos = X[X['ttype'] == POS_TWEET]
    
    neg_date = neg[neg['tdate'] < date_to]
    pos_date = pos[pos['tdate'] < date_to]
    
    if step == 'minute':
        step = 60
    elif step == 'hour':
        step = 60*60
    elif step == 'day':
        step = 60*60*24
    elif step == 'week':
        step = 60*60*24*7

    step *= step_count
    
    pos_count = list()
    neg_count = list()
    
    dates_in_range = range(date_from, date_to, step)
    
    for date in dates_in_range:
        if by_blocks:
            pos_count.append(pos_date[(pos_date['tdate'] > date) & (pos_date['tdate'] < (date + step))].shape[0])
            neg_count.append(neg_date[(neg_date['tdate'] > date) & (neg_date['tdate'] < (date + step))].shape[0])
        else:
            pos_count.append(pos_date[pos_date['tdate'] < date].shape[0])
            neg_count.append(neg_date[neg_date['tdate'] < date].shape[0])
            
    dates_in_range = [d*1000 for d in dates_in_range]
    return dates_in_range, pos_count, neg_count

tknzr = TweetTokenizer()
def tweet_tokenize(msg):
    return tknzr.tokenize(msg)

def remove_retweet(msg):
    return ' '.join(filter(lambda x:x[0]!='@' and not x.startswith('http'), msg.split()))

def preprocess_tweet(text):
    return vectorizer.transform([remove_retweet(text)])

SENTIMENT_THRESHOLD = 0.7
def predict_sentiment(text):
    return model.predict(preprocess_tweet(text))[0]

class MyStreamListener(tweepy.streaming.StreamListener):
    def on_status(self, status):
        msg = {'name': status.user.name, 'time': str(status.created_at), 'text': status.text, 'sentiment': predict_sentiment(status.text), 'geo': status.geo}

        with lock:
            if len(last_tweets) > 4:
                last_tweets.popleft()

            last_tweets.append(msg)

        TweetsNamespace.broadcast('tweet_text', json.dumps(msg))

class TweetsNamespace(BaseNamespace):
    sockets = {}

    def recv_connect(self):
        print "Got a socket connection" # debug
        self.sockets[id(self)] = self

    def disconnect(self, *args, **kwargs):
        print "Got a socket disconnection" # debug
        if id(self) in self.sockets:
            del self.sockets[id(self)]

        super(TweetsNamespace, self).disconnect(*args, **kwargs)
    # broadcast to all sockets on this channel!

    @classmethod
    def broadcast(self, event, message):
        for ws in self.sockets.values():
            ws.emit(event, message)

#Listening to web socket
@app.route('/socket.io/<path:rest>')
def push_stream(rest):
    try:
        socketio_manage(request.environ, {'/tweets': TweetsNamespace}, request)
        return ''
    except:
        app.logger.error("Exception while handling socketio connection", exc_info=True)

@app.route('/')
def hello_world():
    return render_template('index.html', data='test')

@app.route('/live-data')
def live_data():
    with lock:
        data = {'overall_pos': zip(overall_data[0], overall_data[1]), 'overall_neg': zip(overall_data[0], overall_data[2]),
                'blocks_pos': zip(blocks_data[0], blocks_data[1]), 'blocks_neg': zip(blocks_data[0], blocks_data[2]),
                'pos_geo': pos_geo, 'neg_geo': neg_geo, 'last_tweets': list(last_tweets)}

    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

def convert_to_geo(pnt):
    pnts = map(float, pnt.split(','))

    return {'lat':pnts[0], 'lon':pnts[1]}

def get_latest_tweets(X, count):
    X = X.sort('tdate')
    res = deque()

    for i in range(X.shape[0] - count, X.shape[0]):
        tw = X.iloc[i, ]
        tw = {'name':tw['tname'], 'time':datetime.datetime.fromtimestamp(tw['tdate']).strftime('%Y-%m-%d %H:%M:%S'),
              'text':tw['ttext'], 'sentiment':tw['ttype'], 'geo': None}

        res.append(tw)

    return res

keywords = [u'МФТИ', u'физико-технический институт', u'МГУ', u'СПбАУ', u'СПбГУ', u'ИТМО'] #need many tweets for testing
#keywords = ['Trump']
if __name__ == '__main__':
    print '*** Loading started ***'
    start_time = time.time()

    with open('models/model_sgd.pkl', 'rb') as f:
        model = pickle.load(f)

    with open('models/vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)

    print '*** Loading completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2)  

    X = pd.read_csv('data/old_tweets/MIPT.csv', sep=';', na_values='None')
    X['tdate'] = X['tdate'].apply(lambda x: int(time.mktime(datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S").timetuple())))
    X['ttext'] = X['ttext'].apply(remove_retweet)
    X['ttype'] = model.predict(vectorizer.transform(X['ttext']))

    overall_data = date_distribution(X, X['tdate'].min(), X['tdate'].max(), step = 'minute')
    blocks_data = date_distribution(X, X['tdate'].min(), X['tdate'].max(), step = 'hour', by_blocks = True, step_count = 4)
    pos_geo = list(X.dropna()['tgeo'][X['ttype'] == POS_TWEET].apply(convert_to_geo))
    neg_geo = list(X.dropna()['tgeo'][X['ttype'] == NEG_TWEET].apply(convert_to_geo))

    last_tweets = get_latest_tweets(X, 5)

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    print '*** Stream started *** %s' % str(datetime.datetime.now().time())

    myStream = tweepy.Stream(auth = auth, listener = MyStreamListener())

    listener_thread = threading.Thread(target = myStream.filter,
                                               kwargs = dict(follow = None, track = keywords))
    listener_thread.daemon = True
    listener_thread.start()

    port = int(os.environ.get('PORT', 5000))
    SocketIOServer(('0.0.0.0', port), app, resource = 'socket.io').serve_forever()
