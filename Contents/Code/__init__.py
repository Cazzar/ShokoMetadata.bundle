import os, re, time, string, thread, threading, urllib, copy
from lxml import etree
from datetime import datetime
import TagBlacklist

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

class ShokoCommonAgent:
    def Search(self, results, media, lang, manual, movie):
        name = media.show
        
        #http://127.0.0.1:8111/api/serie/search?query=Clannad&level=1&apikey=d422dfd2-bdc3-4219-b3bb-08b85aa65579

        pelimresults = HttpReq("api/serie/search?query=%s&level=%d&fuzzy=true" % (urllib.quote(name), 0))
        i = 0
        for result in pelimresults:
            score = 100 if result['title'] == name else 85 #TODO: Improve this to respect synonyms./
            meta = MetadataSearchResult('%s' % result['id'], result['title'], result['year'], score, lang)
            results.Append(meta)

        #results.Sort('score', descending=True)

    def Update(self, metadata, media, lang, force, movie):
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

        TagBlacklist.processTags(tags)

        metadata.genres = tags

        if (len(series['art']['banner'])):
            for art in series['art']['banner']:
                metadata.banner[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])

        if (len(series['art']['thumb'])):
            for art in series['art']['thumb']:
                metadata.posters[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])

        if (len(series['art']['fanart'])):
            for art in series['art']['fanart']:
                metadata.art[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])

        ### Generate general content ratings.
        ### VERY rough approximation to: https://www.healthychildren.org/English/family-life/Media/Pages/TV-Ratings-A-Guide-for-Parents.aspx

        if (Prefs["Ratings"]):
            if ('Kodomo' in tags):
                metadata.content_rating = 'TV-Y'

            if ('Mina' in tags):
                metadata.content_rating = 'TV-G'

            if ('Shoujo' in tags):
                metadata.content_rating = 'TV-14'

            if ('Shounen' in tags):
                metadata.content_rating = 'TV-14'

            if ('Josei' in tags):
                metadata.content_rating = 'TV-14'

            if ('Seinen' in tags):
                metadata.content_rating = 'TV-MA'

            if ('18 Restricted' in tags):
                metadata.content_rating = 'TV-R'
            
            Log('Assumed tv rating to be: %s' % metadata.content_rating)

        if (not movie):
            for ep in series['eps']:
                if ep['eptype'] != 1:
                    continue

                season = 1
                try:
                    season = int(ep['season'].split(x)[0])
                except:
                    pass

                episodeObj = metadata.seasons[season].episodes[ep['epnumber']]
                episodeObj.title = ep['title']
                episodeObj.summary = ep['summary']

                if ep['air'] != '1/01/0001 12:00:00 AM':
                    episodeObj.originally_available_at = datetime.strptime(ep['air'], "%d/%m/%Y %H:%M:%S %p").date()

                if (len(series['art']['thumb'])):
                    for art in series['art']['thumb']:
                        episodeObj.thumbs[art['url']] = Proxy.Media(HTTP.Request(art['url']).content, art['index'])


def try_to_remove(arr, val):
    try:
        arr.remove(val)
    except:
        pass

class ShokoTVAgent(Agent.TV_Shows, ShokoCommonAgent):
  name, primary_provider, fallback_agent, contributes_to, accepts_from = ('ShokoTV', True, False, ['com.plexapp.agents.hama'], ['com.plexapp.agents.localmedia'] ) #, 'com.plexapp.agents.opensubtitles'
  languages = [Locale.Language.English, 'fr', 'zh', 'sv', 'no', 'da', 'fi', 'nl', 'de', 'it', 'es', 'pl', 'hu', 'el', 'tr', 'ru', 'he', 'ja', 'pt', 'cs', 'ko', 'sl', 'hr']
  def search(self, results, media, lang, manual): self.Search(results, media, lang, manual, False)
  def update(self, metadata, media, lang, force ): self.Update(metadata, media, lang, force, False)

class ShokoMovieAgent(Agent.Movies, ShokoCommonAgent):
  name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = ('ShokoMovies', True, False, ['com.plexapp.agents.hama'], [Locale.Language.English,], ['com.plexapp.agents.localmedia'] ) #, 'com.plexapp.agents.opensubtitles'
  def search(self, results, media, lang, manual): self.Search(results, media, lang, manual, True)
  def update(self, metadata, media, lang, force ): self.Update(metadata, media, lang, force, True)