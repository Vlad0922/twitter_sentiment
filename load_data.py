# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

import pickle

from tweepy import API as tweepy_API
from tweepy import OAuthHandler
from tweepy import Cursor

from nltk.tokenize.casual import TweetTokenizer

from sqlalchemy import create_engine

import codecs

tknzr = TweetTokenizer()
def tweet_tokenize(msg):
    return tknzr.tokenize(msg)

def remove_retweet(msg):
    return ' '.join(filter(lambda x:x[0]!='@' and not x.startswith('http'), msg.split()))

NEG_TWEET = -1
POS_TWEET = 1
NEUT_TWEET = 0

SENTIMENT_THRESHOLD = 0.6
def convert_proba(p):
    if p[0] >= SENTIMENT_THRESHOLD:
        return NEG_TWEET
    elif p[1] >= SENTIMENT_THRESHOLD:
        return POS_TWEET
    else:
        return NEUT_TWEET

keywords = {
    'MIPT': ' OR '.join([u'МФТИ', u'физтех', u'\"Московский физико-технический институт\"']),
    # 'MSU':  u'МГУ', #MSU count as Michigan state university in most tweets
    # 'ITMO': u'ИТМО',
    # 'SPAU': u'СПбАУ',
    # 'SPBU': u'СПбГУ'
}

if __name__ == '__main__':    
    #load twitter API tokens from file  
    with open('webapp/tokens.txt') as f:
        (access_token, access_token_secret,
            consumer_key, consumer_secret) = f.read().split()

    with open('webapp/db_conf.txt') as f:
        psql_name, psql_pass = f.read().split()

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy_API(auth)

    for u in keywords:
        finded = 0

        engine = create_engine('postgresql://%s:%s@localhost/tweets_db' % (psql_name, psql_pass))
 
        X = pd.DataFrame(columns=['tname', 'tdate', 'ttext', 'tgeo', 'tid'])

        for tweet in Cursor(api.search, q=keywords[u], 
                            rpp=100, result_type="recent").items():
            finded += 1

            msg = tweet.text.replace('\n', ' ').replace('\r', ' ').replace(';', '')
            coord = tweet.geo
            if coord != None:
                coord = ','.join(map(str, coord['coordinates']))

            row = pd.Series({'tname': tweet.user.name, 'tdate': str(tweet.created_at), 'ttext': msg, 'tgeo': str(coord), 'tid': tweet.id_str})
            X = X.append(row, ignore_index = True)

        with open('webapp/models/model_sgd.pkl', 'rb') as f:
            model = pickle.load(f)

        with open('webapp/models/vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)

        X['ttype'] = np.apply_along_axis(convert_proba, 1, model.predict_proba(vectorizer.transform(X['ttext'].apply(remove_retweet))))

        #hm...delete nonunique tweets?
        # X_exist = pd.read_sql_table('tweets', engine)
        # X = pd.concat([X, X_exist])

        X.to_sql('tweets', engine, if_exists='replace', index = False)

        print u, X.shape[0]
