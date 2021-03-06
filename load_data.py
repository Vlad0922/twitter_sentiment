    # -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

import pickle
import ConfigParser

from tweepy import API as tweepy_API
from tweepy import OAuthHandler
from tweepy import Cursor

from nltk.tokenize.casual import TweetTokenizer

from sqlalchemy import create_engine

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
    'МФТИ': ' OR '.join([u'МФТИ', u'физтех', u'\"Московский физико-технический институт\"']),
    'МГУ':  ' OR '.join([u'МГУ', u'\"Московский государственный университет\"']), 
    'ИТМО': ' OR '.join([u'ИТМО', u'\"Санкт-Петербургский национальный исследовательский университет информационных технологий, механики и оптики\"']),
    #'СПбАУ': ' OR '.join([u'СПбАУ', u'\"Академический университет\"']),
    'СПбГУ': ' OR '.join([u'СПбГУ', u'\"Санкт-Петербургский государственный университет\"'])
}

if __name__ == '__main__':    
    config = ConfigParser.ConfigParser()
    config.read('webapp/config.ini') 

    auth = OAuthHandler(config.get('TwitterKeys', 'consumer_key'), config.get('TwitterKeys', 'consumer_secret'))
    auth.set_access_token(config.get('TwitterKeys', 'access_token'), config.get('TwitterKeys', 'access_token_secret'))
    api = tweepy_API(auth)

    engine = create_engine('postgresql://%s:%s@localhost/tweets_db' %
                        (config.get('DatabaseLogin', 'login'), config.get('DatabaseLogin', 'password')))
 
    X = pd.DataFrame(columns=['tname', 'tdate', 'ttext', 'tgeo', 'tid', 'tuniversity'])

    for u in keywords:
        finded = 0

        try:
            X_current = pd.DataFrame(columns=['tname', 'tdate', 'ttext', 'tgeo', 'tid'])
            for tweet in Cursor(api.search, q=keywords[u], 
                                rpp=100, result_type="recent").items():

                msg = tweet.text.replace('\n', ' ').replace('\r', ' ').replace(';', '')
                coord = tweet.geo
                if coord != None:
                    coord = ','.join(map(str, coord['coordinates']))

                row = pd.Series({'tname': tweet.user.name, 'tdate': str(tweet.created_at), 'ttext': msg, 'tgeo': str(coord), 'tid': tweet.id_str})
                X_current = X_current.append(row, ignore_index = True)

                finded += 1
                if finded >= 800: #twitter API limit is 2500 tweets. Some universities are popular (MSU for example) and can exceed limit.
                    break
        except:
            print 'twitter API limit exceed'


        print u, X_current.shape[0]

        X_current['tuniversity'] = u

        X = pd.concat([X, X_current], ignore_index = True)

    with open('webapp/models/model_sgd.pkl', 'rb') as f:
        model = pickle.load(f)

    with open('webapp/models/vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)

    X['ttype'] = np.apply_along_axis(convert_proba, 1, model.predict_proba(vectorizer.transform(X['ttext'].apply(remove_retweet))))

    X_exist = pd.read_sql_table('tweets', engine)
    last_time = X_exist['tdate'].max()
    X = X[X['tdate'] > last_time]
    X = pd.concat([X_exist, X])

    X.to_sql('tweets', engine, if_exists='replace', index = False)
