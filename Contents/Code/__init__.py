import os, re, time, string, thread, threading, urllib, copy
from lxml import etree

API_KEY = ''
PLEX_HOST = ''

def ValidatePrefs():
    pass

def Start():
    Log("Shoko metata agent started")
    HTTP.Headers['Accept'] = 'application/json'
    ValidatePrefs()

def GetApiKey():
    global API_KEY

    if not API_KEY:
        data = '{"user":"%s", "pass":"%s", "device":"%s"}' % (Prefs['Username'], Prefs['Password'] if Prefs['Password'] != None else '', 'Shoko Metadata For Plex')
        resp = HttpPost('api/auth', data)['apikey']
        Log.Debug("Got API KEY: %s" % resp)
        API_KEY = resp
        return resp
    
    return API_KEY
        

def HttpPost(url, postdata):
    myheaders = {'Content-Type': 'application/json'}
    return JSON.ObjectFromString(HTTP.Request('http://%s:%s/%s' % (Prefs['Hostname'], Prefs['Port'], url), headers=myheaders, data=postdata).content)

def HttpReq(url, authenticate = True):
    Log("Requesting: %s" % url)
    apistring = ''
    if authenticate: 
        apistring = '&apikey=%s' % GetApiKey()

    return JSON.ObjectFromString(HTTP.Request('http://%s:%s/%s%s' % (Prefs['Hostname'], Prefs['Port'], url, apistring)).content)

class ShokoTVAgent(Agent.TV_Shows):
    name = 'Shoko' 
    languages = [ Locale.Language.English, ] 
    primary_provider = True 
    fallback_agent = False 
    accepts_from = ['com.plexapp.agents.hama'] 
    contributes_to = None

    def search(self, results, media, lang):
        name = media.show
        
        #http://127.0.0.1:8111/api/serie/search?query=Clannad&level=1&apikey=d422dfd2-bdc3-4219-b3bb-08b85aa65579

        pelimresults = HttpReq("api/serie/search?query=%s&level=%d&fuzzy=true" % (urllib.quote(name), 0))
        i = 0
        for result in pelimresults:
            score = 100 if result['title'] == name else 85 #TODO: Improve this to respect synonyms./
            meta = MetadataSearchResult('%s' % result['id'], result['title'], result['year'], score, lang)
            results.Append(meta)

        #results.Sort('score', descending=True)

    def update(self, metadata, media, lang):
        Log("update(%s)" % metadata.id)
        aid = metadata.id
        # title = media.name
        #http://127.0.0.1:8111/api/ep/getbyfilename?apikey=d422dfd2-bdc3-4219-b3bb-08b85aa65579&filename=%5Bjoseole99%5D%20Clannad%20-%2001%20(1280x720%20Blu-ray%20H264)%20%5B8E128DF5%5D.mkv

        # episode_data = HttpReq("api/ep/getbyfilename?apikey=%s&filename=%s" % (GetApiKey(), urllib.quote(media.filename)))
        series = HttpReq("api/serie?id=%s" % aid)

        #build metadata on the TV show.
        metadata.summary = series['summary']
        metadata.title = series['title']
        metadata.rating = float(series['rating'])

        tags = []
        for tag in series['tags']:
            tags.append(tag['tag'])
        
        tags.remove('Meta Tags')
        tags.remove('Cast') #TODO: Work this better.
        tags.remove('TO BE MOVED TO EPISODE')
        tags.remove('TO BE MOVED TO CHARACTER')

        metadata.genres = tags
        Log(tags)

        if (len(series['art']['banner'])):
            for art in series['art']['banner']:
                metadata.banner[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])

        if (len(series['art']['thumb'])):
            for art in series['art']['thumb']:
                metadata.posters[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])

        if (len(series['art']['fanart'])):
            for art in series['art']['fanart']:
                metadata.art[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])