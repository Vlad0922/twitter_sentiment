# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np

import os
import json
import datetime
import time
import threading
import pickle
import urlparse
import copy
import ConfigParser

import tweepy

from sqlalchemy import create_engine, MetaData, Table

from collections import deque

from flask import Flask, render_template, make_response, request

from nltk.tokenize.casual import TweetTokenizer
from nltk.corpus import stopwords

from socketio import socketio_manage
from socketio.namespace import BaseNamespace
from socketio.server import SocketIOServer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier

app = Flask(__name__)

lock = threading.Lock()
last_tweets = deque()

TABLE_SIZE = 10
NEG_TWEET = -1
NEUT_TWEET = 0
POS_TWEET = 1

update_counter = 0
BLOCK_TICK = 15 #update block data every 15 ticks
UPDATE_TICK = 60 #in seconds

def date_distribution(X, date_from, date_to, step = 'day', step_count = 1, by_blocks = False):      
    if step == 'minute':
        step = 60
    elif step == 'hour':
        step = 60*60
    elif step == 'day':
        step = 60*60*24
    elif step == 'week':
        step = 60*60*24*7

    step *= step_count
    
    dates_in_range = range(date_from, date_to + 1, step)
    counts = {s:{u:0 for u in universities} for s in [POS_TWEET, NEG_TWEET, NEUT_TWEET]}    
    date_counts = {s:{u:[] for u in universities} for s in [POS_TWEET, NEG_TWEET, NEUT_TWEET]}

    if by_blocks:
        diff_counts = copy.deepcopy(counts)

    i = 0
    for d in dates_in_range:
        row = X.iloc[i, ]
        while row['tdate'] < d and i < X.shape[0]:
            counts[row['ttype']][row['tuniversity']] += 1

            i += 1
            row = X.iloc[i, ]

        if by_blocks:
            for s in date_counts:
                for u in universities:
                    date_counts[s][u].append(counts[s][u] - diff_counts[s][u])
                    diff_counts[s][u] = counts[s][u]
        else:
            for s in date_counts:
                for u in universities: 
                    date_counts[s][u].append(counts[s][u])
        
    #scale for js       
    dates_in_range = [d*1000 for d in dates_in_range]
    return dates_in_range, date_counts

tknzr = TweetTokenizer()
def tweet_tokenize(msg):
    return tknzr.tokenize(msg)

def remove_retweet(msg):
    return ' '.join(filter(lambda x:x[0]!='@' and not x.startswith('http'), msg.split()))

def preprocess_tweet(text):
    return vectorizer.transform([remove_retweet(text)])

SENTIMENT_THRESHOLD = 0.6
def convert_proba(p):
    if p[0] >= SENTIMENT_THRESHOLD:
        return NEG_TWEET
    elif p[1] >= SENTIMENT_THRESHOLD:
        return POS_TWEET
    else:
        return NEUT_TWEET

def predict_sentiment(text):
    return convert_proba(model.predict_proba(preprocess_tweet(text))[0])

def find_university(text):
    for k in keywords:
        for u in keywords[k]:
            if u.lower() in text.lower():
                return k

class MyStreamListener(tweepy.streaming.StreamListener):
    def on_status(self, status):
        global counts, geo_data, last_tweets

        sentiment = predict_sentiment(status.text)
        msg = { 'type': 'tweet',
                'name': status.user.name, 'time': str(status.created_at), 'text': status.text, 'sentiment': sentiment, 'geo': status.geo, 'id': status.id_str}

        with lock:
            if len(last_tweets) > TABLE_SIZE - 1:
                last_tweets.popleft()

            last_tweets.append(msg)            

            university = find_university(status.text)

            if sentiment == POS_TWEET:
                counts[POS_TWEET][university] += 1
            elif sentiment == NEG_TWEET:
                counts[NEG_TWEET][university] += 1
            else:
                counts[NEUT_TWEET][university] += 1

            if status.geo != None:
                geo_data.append({'lat':status.geo['coordinates'][0], 'lon':status.geo['coordinates'][1]})

        self.send_to_db(status, sentiment, university)
        TweetsNamespace.broadcast('tweet_text', json.dumps(msg))

    def send_to_db(self, tweet, sentiment, university):
        msg = tweet.text.replace('\n', ' ').replace('\r', ' ').replace(';', '')
        coord = tweet.geo
        if coord != None:
            coord = ','.join(map(str, coord['coordinates']))

        tweets_table.insert().execute(tname = tweet.user.name, tdate = str(tweet.created_at), tuniversity = university,
                                      ttext = msg, tgeo = str(coord), tid = tweet.id_str, ttype = sentiment)

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

    @classmethod
    def broadcast(self, event, message):
        for ws in self.sockets.values():
            ws.emit(event, message)

#Слушаем сокет
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
        data = {'overall_time': overall_data[0], 'overall_data': overall_data[1],
                'blocks_time': blocks_data[0], 'blocks_data': blocks_data[1],
                'geo': geo_data, 'last_tweets': list(last_tweets), 'universities': universities}

    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

def send_new_data():
    global update_counter, counts, diffs, overall_data, blocks_data

    current_time = time.time()*1000

    with lock:
        update_counter += 1
        msg = {'type': 'new_data', 'time': current_time, 'overall_data': counts}

        overall_data[0].append(current_time)
        for s in [POS_TWEET, NEG_TWEET, NEUT_TWEET]:
            for u in universities:
                overall_data[1][s][u].append(counts[s][u])        

        if (update_counter % BLOCK_TICK) == 0:
            blocks_data[0].append(current_time)
            for s in [POS_TWEET, NEG_TWEET, NEUT_TWEET]:
                for u in universities:
                    blocks_data[1][s][u].append(counts[s][u] - diffs[s][u])

            new_blocks = dict()
            for s in [POS_TWEET, NEG_TWEET, NEUT_TWEET]:
                new_blocks[s] = dict()
                for u in universities:
                    new_blocks[s][u] = counts[s][u] - diffs[s][u]

            msg['blocks_data'] = new_blocks

            diffs = copy.deepcopy(counts)

    TweetsNamespace.broadcast('tweet_text', json.dumps(msg))
    threading.Timer(UPDATE_TICK, send_new_data).start()

def convert_to_geo(pnt):
    pnts = map(float, pnt.split(','))

    return {'lat':pnts[0], 'lon':pnts[1]}

def get_latest_tweets(X, count):
    res = deque()

    # tweets are sorted
    for i in range(X.shape[0] - count, X.shape[0]):  
        tw = X.iloc[i, ]
        tw = {'name':tw['tname'], 'time': datetime.datetime.fromtimestamp(tw['tdate']).strftime('%Y-%m-%d %H:%M:%S'),
              'text':tw['ttext'], 'sentiment':tw['ttype'], 'geo': None, 'id': tw['tid']}

        res.append(tw)

    return res

keywords = {u'МФТИ':[u'МФТИ', u'физтех'], u'МГУ':[u'МГУ'], u'СПбГУ':[u'СПбГУ'], u'ИТМО':[u'ИТМО']} 
if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read('config.ini')

    print '*** Loading started ***'
    start_time = time.time()

    with open('models/model_sgd.pkl', 'rb') as f:
        model = pickle.load(f)

    with open('models/vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)

    print '*** Loading completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2) 
    start_time = time.time()

    if 'DATABASE_URL' in os.environ:
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.environ["DATABASE_URL"])

        engine = create_engine('postgresql://%s:%s@%s:%s/%s' % (url.username, url.password, url.hostname, url.port, url.path[1:]))
    else:
        engine = create_engine('postgresql://%s:%s@localhost/tweets_db' %
                                (config.get('DatabaseLogin', 'login'), config.get('DatabaseLogin', 'password')))

    metadata = MetaData(bind = engine)
    tweets_table = Table('tweets', metadata, autoload = True)

    X = pd.read_sql_table('tweets', engine)
    #need presorted values
    X = X.sort_values(by = 'tdate')

    print '*** Load from db completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2) 
    start_time = time.time()
    
    X['tdate'] = X['tdate'].apply(lambda x: int(time.mktime(datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S').timetuple())))
    X['tgeo'] = X['tgeo'].apply(lambda x: None if x == 'None' else x)

    print '*** Data transform: %s minutes ***' % round(((time.time() - start_time) / 60), 2) 
    start_time = time.time()

    universities = list(X['tuniversity'].unique())

    overall_data = list(date_distribution(X, X['tdate'].min(), X['tdate'].max(), step = 'minute'))
    blocks_data = list(date_distribution(X, X['tdate'].min(), X['tdate'].max(), step = 'hour', by_blocks = True, step_count = 4))
    geo_data = list(X.dropna()['tgeo'].apply(convert_to_geo))

    last_tweets = get_latest_tweets(X, TABLE_SIZE)

    counts = {s:{u:X[(X['tuniversity'] == u) & (X['ttype'] == s)].shape[0] for u in universities} for s in [POS_TWEET, NEG_TWEET, NEUT_TWEET]}
    diffs = copy.deepcopy(counts)

    print '*** Global data loading completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2) 

    auth = tweepy.OAuthHandler(config.get('TwitterKeys', 'consumer_key'), config.get('TwitterKeys', 'consumer_secret'))
    auth.set_access_token(config.get('TwitterKeys', 'access_token'), config.get('TwitterKeys', 'access_token_secret'))

    myStream = tweepy.Stream(auth = auth, listener = MyStreamListener(), include_entities = True)
    myStream.filter(track = [item for key in keywords for item in keywords[key]], async = True)

    threading.Timer(UPDATE_TICK, send_new_data).start()

    print '*** Stream started *** %s' % str(datetime.datetime.now().time())

    port = int(os.environ.get('PORT', 5000))
    SocketIOServer(('0.0.0.0', port), app, resource = 'socket.io').serve_forever()

