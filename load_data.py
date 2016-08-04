# -*- coding: utf-8 -*-
import pandas as pd

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

keywords = {
    'MIPT': ' OR '.join([u'МФТИ', u'физтех', u'\"Московский физико-технический институт\"']),
    #'MSU':  u'МГУ', #MSU count as Michigan state university in most tweets
    # 'ITMO': u'ИТМО',
    # 'SPAU': u'СПбАУ',
     #'SPBU': u'СПбГУ'
}

if __name__ == '__main__':    
    #load twitter API tokens from file  
    with open('tokens.txt') as f:
        (access_token, access_token_secret,
            consumer_key, consumer_secret) = f.read().split()

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy_API(auth)

    for u in keywords:
        finded = 0

        engine = create_engine('sqlite:///webapp/data/tweets.db')
        X = pd.DataFrame(columns=['tname', 'tdate', 'ttext', 'tgeo'])

        # f = codecs.open('webapp/data/old_tweets/' + u + '.csv', 'w', 'utf-8')
        # f.write(columns)


        for tweet in Cursor(api.search, q=keywords[u], 
                            rpp=100, result_type="recent").items():
            finded += 1

            msg = tweet.text.replace('\n', ' ').replace('\r', ' ').replace(';', '')
            coord = tweet.geo
            if coord != None:
                coord = ','.join(map(str, coord['coordinates']))

            row = pd.Series({'tname': tweet.user.name, 'tdate': str(tweet.created_at), 'ttext': msg, 'tgeo': str(coord)})

            X = X.append(row, ignore_index = True)

        with open('webapp/models/model_sgd.pkl', 'rb') as f:
            model = pickle.load(f)

        with open('webapp/models/vectorizer.pkl', 'rb') as f:
            vectorizer = pickle.load(f)

        X['ttype'] = model.predict(vectorizer.transform(X['ttext'].apply(remove_retweet)))
        X = X.sort('tdate')

        X.to_sql('tweets', engine, if_exists='append', index = False)

        print u, X.shape[0]
