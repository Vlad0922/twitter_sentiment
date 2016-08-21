# -*- coding: utf-8 -*-

import pandas as pd

import os
import json
import datetime
import time
import threading
import pickle
import urlparse

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

with open('tokens.txt') as f:
    (access_token, access_token_secret,
        consumer_key, consumer_secret) = f.read().split()

with open('db_conf.txt') as f:
    psql_name, psql_pass = f.read().split()

def date_distribution(X, date_from, date_to, step = 'day', step_count = 1, by_blocks = False):
    #is it a bug? values in db isnt sorted
    #X = X[X['tdate'] <= date_to].sort_values(by = 'tdate')
       
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
    pos_count = list()
    neg_count = list()
    neut_count = list()

    i = 0
    pos_total = 0
    neg_total = 0
    neut_total = 0

    if by_blocks:
        pos_diff = 0
        neg_diff = 0
        neut_diff = 0

    for d in dates_in_range:
        row = X.iloc[i, ]
        while row['tdate'] < d and i < X.shape[0]:
            if row['ttype'] == POS_TWEET:
                pos_total += 1
            elif row['ttype'] == NEG_TWEET:
                neg_total += 1
            else:
                neut_total += 1

            i += 1
            row = X.iloc[i, ]

        if by_blocks:
            pos_count.append(pos_total - pos_diff)
            neg_count.append(neg_total - neg_diff)
            neut_count.append(neut_total - neut_diff)

            pos_diff = pos_total
            neg_diff = neg_total
            neut_diff = neut_total
        else:
            pos_count.append(pos_total)
            neg_count.append(neg_total)
            neut_count.append(neut_total)
        
    #scale for js       
    dates_in_range = [d*1000 for d in dates_in_range]
    return dates_in_range, pos_count, neg_count, neut_count

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

class MyStreamListener(tweepy.streaming.StreamListener):
    def on_status(self, status):
        sentiment = predict_sentiment(status.text)
        msg = { 'type': 'tweet',
                'name': status.user.name, 'time': str(status.created_at), 'text': status.text, 'sentiment': sentiment, 'geo': status.geo, 'id': status.id_str}

        with lock:
            if len(last_tweets) > TABLE_SIZE - 1:
                last_tweets.popleft()

            last_tweets.append(msg)

            global pos_count, neg_count, neut_count, geo_data 

            if sentiment == POS_TWEET:
                pos_count += 1
            elif sentiment == NEG_TWEET:
                neg_count += 1
            else:
                neut_count += 1

            if status.geo != None:
                geo_data.append({'lat':status.geo['coordinates'][0], 'lon':status.geo['coordinates'][1]})

        self.send_to_db(status, sentiment)
        TweetsNamespace.broadcast('tweet_text', json.dumps(msg))

    def send_to_db(self, tweet, sentiment):
        msg = tweet.text.replace('\n', ' ').replace('\r', ' ').replace(';', '')
        coord = tweet.geo
        if coord != None:
            coord = ','.join(map(str, coord['coordinates']))

        tweets_table.insert().execute(tname = tweet.user.name, tdate = str(tweet.created_at),
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
        data = {'overall_pos': zip(overall_data[0], overall_data[1]), 'overall_neg': zip(overall_data[0], overall_data[2]), 'overall_neut': zip(overall_data[0], overall_data[3]),
                'blocks_pos': zip(blocks_data[0], blocks_data[1]), 'blocks_neg': zip(blocks_data[0], blocks_data[2]), 'blocks_neut': zip(blocks_data[0], blocks_data[3]),
                'geo': geo_data, 'last_tweets': list(last_tweets)}

    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

def send_new_data():
    global update_counter, neg_diff, pos_diff, neut_diff, overall_data, blocks_data

    current_time = time.time()*1000

    with lock:
        update_counter += 1
        msg = {'type': 'new_data', 'time': current_time, 'overall_pos': pos_count, 'overall_neg': neg_count, 'overall_neut': neut_count}
        overall_data[0].append(current_time)
        overall_data[1].append(pos_count)
        overall_data[2].append(neg_count)
        overall_data[3].append(neut_count)

        if (update_counter % BLOCK_TICK) == 0:
            msg['blocks_pos'] = pos_count - pos_diff
            msg['blocks_neg'] = neg_count - neg_diff
            msg['blocks_neut'] = neut_count - neut_diff

            blocks_data[0].append(current_time)
            blocks_data[1].append(pos_count - pos_diff)
            blocks_data[2].append(neg_count - neg_diff)
            blocks_data[3].append(neut_count - neut_diff)

            pos_diff = pos_count
            neg_diff = neg_count
            neut_diff = neut_count

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

keywords = [u'МФТИ', u'физико-технический институт', u'МГУ', u'СПбАУ', u'СПбГУ', u'ИТМО'] 
#keywords = ['Trump'] #need many tweets for testing
if __name__ == '__main__':
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
        engine = create_engine('postgresql://%s:%s@localhost/tweets_db' % (psql_name, psql_pass))

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

    overall_data = list(date_distribution(X, X['tdate'].min(), X['tdate'].max(), step = 'minute'))
    blocks_data = list(date_distribution(X, X['tdate'].min(), X['tdate'].max(), step = 'hour', by_blocks = True, step_count = 4))
    geo_data = list(X.dropna()['tgeo'].apply(convert_to_geo))

    last_tweets = get_latest_tweets(X, TABLE_SIZE)

    value_counts = X['ttype'].value_counts().to_dict()
    pos_count = value_counts[POS_TWEET]
    neg_count = value_counts[NEG_TWEET]
    neut_count = value_counts[NEUT_TWEET]

    pos_diff = pos_count
    neg_diff = neg_count
    neut_diff = neut_count

    print '*** Global data loading completed: %s minutes ***' % round(((time.time() - start_time) / 60), 2) 

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    myStream = tweepy.Stream(auth = auth, listener = MyStreamListener(), include_entities = True)
    myStream.filter(track = keywords, async = True)

    threading.Timer(UPDATE_TICK, send_new_data).start()

    print '*** Stream started *** %s' % str(datetime.datetime.now().time())

    port = int(os.environ.get('PORT', 5000))
    SocketIOServer(('0.0.0.0', port), app, resource = 'socket.io').serve_forever()

