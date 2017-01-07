import os, re, time, string, thread, threading, urllib, copy
from lxml import etree

API_KEY = ''
PLEX_HOST = ''

def ValidatePrefs():
    PLEX_HOST = "http://%s:%s" % (Prefs['Hostname'], Prefs['Port'])

    data = '{"user":"%s", "pass":"%s", "device":"%s"}' % (Prefs['Username'], Prefs['Password'] if Prefs['Password'] != None else '', 'Shoko Metadata For Plex')
    API_KEY = HttpReq('%s/api/auth' % PLEX_HOST, data)['apikey']

def Start():
    Log("Shoko metata agent started")
    HTTP.Headers['Accept'] = 'application/json'
    ValidatePrefs()

def HttpReq(url, postdata=None):
    myheaders = None;
    if postdata != None:
        myheaders = {'Content-Type': 'application/json'}
    
    Log("Requesting: %s" % URL)
    return JSON.ObjectFromString(HTTP.Request(url, headers=myheaders, data=postdata).content)

class ShokoTVAgent(Agent.TV_Shows):
    name = 'Shoko' 
    languages = [ Locale.Language.English, ] 
    primary_provider = True 
    fallback_agent = False 
    accepts_from = None 
    contributes_to = None

    def search(self, results, media, lang, manual):
        name = media.primary_metadata.name
        #http://127.0.0.1:8111/api/serie/search?query=Clannad&level=1&apikey=d422dfd2-bdc3-4219-b3bb-08b85aa65579

        results = HttpReq("%s/api/serie/search?query=%s&level=%d&apikey=%s" % (PLEX_HOST, urllib.quote(name), 0, API_KEY))
        Log(results[0].title)
        pass

    def update(self, metadata, media, lang, force):
        title = media.show
        metadata.title = "Clannad"
        metata.summary = "This is something else"