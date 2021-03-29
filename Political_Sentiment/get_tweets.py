import requests
import base64
import pandas as pd
import contractions
import nltk
import emoji
from nltk.tokenize import word_tokenize


def tweet_generator(tweets):
    for tweet in tweets:
        modified_tweet= {}
        #Write your code here
        for key in tweet.keys():
            if key == "user":
                modified_tweet['user_id'] = tweet[key]['id']
                modified_tweet[key] = tweet[key]
#                 modified_tweet['language'] = tweet[key]['lang']
            elif key == "retweeted_status":
                modified_tweet['retweeted_status_id'] = tweet['retweeted_status']['id']
            else:
                modified_tweet[key] = tweet[key]    
        yield modified_tweet       

def get_things(stuff, things, other):
    wants = []
    desires = stuff[things]
    for craving in desires:
        wants.append(craving[other])
    return ', '.join(wants)
            
            
def get_tweets(topic, num_tweets):
    client_key = 'ewPUfTdoDE8wPq5rLulYVOOBk' #write your API key
    client_secret =  'RQax6aRXZ09m2TJ3RYckOmU4Q1UZTkCT54px7JIMh1XVeZYOXm' #write your API secret key 

    key_secret = '{}:{}'.format(client_key, client_secret).encode('ascii')
    b64_encoded_key = base64.b64encode(key_secret)
    b64_encoded_key = b64_encoded_key.decode('ascii')

    base_url = 'https://api.twitter.com/'
    auth_endpoint = base_url+'oauth2/token'

    auth_headers = { 'Authorization': 'Basic {}'.format(b64_encoded_key),
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}

    auth_data = { 'grant_type': 'client_credentials'}

    response = requests.post(auth_endpoint, headers=auth_headers, data=auth_data)
    print(response.status_code)

    json_data =  response.json()
#     print(json_data)

    access_token = json_data['access_token']

    max_tweets=num_tweets
    tw_limit=100# we can get only 100 tweet per call with standard search api
    tweets = []

    search_headers = {'Authorization': 'Bearer {}'.format(access_token)    
    }

    parameters = { 'q': topic,
                        'result_type': 'recent',
                    'count': 100 }

    search_url = base_url+'1.1/search/tweets.json'

    response = requests.get(search_url, headers=search_headers, params=parameters)

    tweets_json = response.json()

    tweets += tweets_json['statuses']

    ids = [tw['id'] for tw in tweets_json['statuses']]
    min_id = min(ids)

    tw_ids = []
    tw_ids += ids

    for  i in range(max_tweets//tw_limit -1):
        parameters = { 'q': topic,
                        'result_type': 'recent',
                    'count': tw_limit,
                      'max_id': min_id
                     }
        print("searching tweets with id  < {}".format(min_id))
        search_url = base_url+'1.1/search/tweets.json'
        response = requests.get(search_url, headers=search_headers, params=parameters)
        tweets_json = response.json()
        ids = [tw['id'] for tw in tweets_json['statuses']]
        tw_ids += ids
#         print(i, len(tweets_json['statuses']))
        min_id = min(ids)
        tweets += tweets_json['statuses']

    
    tweets_df = pd.DataFrame(tweet_generator(tweets))

    tweets_df.created_at = pd.to_datetime(tweets_df.created_at)

    tweets_df['hashtags'] = tweets_df['entities'].apply(get_things, args=('hashtags', 'text'))
    tweets_df['user_mentions'] = tweets_df['entities'].apply(get_things, args=('user_mentions', 'name'))
    tweets_df['topic'] = topic
    return tweets_df

def text_cleaner(text):
    # Expanding contractions
#     text = sample_contraction_replacer.do_contraction_normalization(text)
    import contractions
    import nltk
    import emoji
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    stopwords = nltk.corpus.stopwords.words('english')
    wnetl = WordNetLemmatizer()
    text = contractions.fix(text)
    # Removing stop words
    tokens = word_tokenize(text)
    new_tokens = [w for w in tokens if w not in stopwords]
    # Lemmatizing
    text = ' '.join([wnetl.lemmatize(w) for w in new_tokens])
    return text

def clean_tweets(data):
    from nltk.stem import WordNetLemmatizer
    import re
    rt = r'RT'
    rt_pattern = re.compile(rt)

    reference = r'\@\w+:|\@\w+'
    reference_re = re.compile(reference)

    pattern = r'https://t.co/[A-Z0-9._%+-]+'
    dots = re.compile(pattern, flags=re.IGNORECASE)
    data['text'] = data['text'].str.replace(rt_pattern, '').str.replace(reference_re, '').str.replace(dots, '').str.replace(r'^.\s+', '').str.replace('\n', ' . ')

    data['emoji'] = data['text'].apply(lambda x: [(c, emoji.UNICODE_EMOJI[c]) for c in x if c in emoji.UNICODE_EMOJI])
    
    stopwords = nltk.corpus.stopwords.words('english')

    wnetl = WordNetLemmatizer()

    def text_cleaner(text):
        # Expanding contractions
    #     text = sample_contraction_replacer.do_contraction_normalization(text)
        text = contractions.fix(text)
        # Removing stop words
        tokens = word_tokenize(text)
        new_tokens = [w for w in tokens if w not in stopwords]
        # Lemmatizing
        text = ' '.join([wnetl.lemmatize(w) for w in new_tokens])
        return text
    
    data['tweet_len'] = data.text.apply(len)

    data_cleaner = data[data.tweet_len >= 3]

    def replace_foreign_characters(s):
        return re.sub(r'[^\x00-\x7f]',r'', s)

    data_cleaner['text'] = data_cleaner['text'].apply(lambda x: replace_foreign_characters(x)).str.strip()

    data_cleaner['text'] = data_cleaner.text.apply(text_cleaner)
    
    return data_cleaner