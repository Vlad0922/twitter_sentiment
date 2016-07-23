# -*- coding: utf-8 -*-

from tweepy import API as tweepy_API
from tweepy import OAuthHandler
from tweepy import Cursor

import codecs

keywords = {
    #'MIPT': ' OR '.join([u'МФТИ', u'физтех', u'\"Московский физико-технический институт\"']),
    #'MSU':  u'МГУ', #MSU count as Michigan state university in most tweets
    'ITMO': u'ИТМО',
    'SPAU': u'СПбАУ',
    'SPBU': u'СПбГУ'
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

        f = codecs.open('data/old_tweets/' + u + '.csv', 'w', 'utf-8')

        for tweet in Cursor(api.search, q=keywords[u], 
                            rpp=100, result_type="recent").items():
            finded += 1

            msg = tweet.text.replace('\n', ' ').replace('\r', ' ')
            f.write(str(tweet.created_at) + ';' + msg + '\n')

        print u, finded
        f.close()
