import os
import re
import time
import string
import thread
import threading
import urllib
import copy
import json
from urllib2 import HTTPError
from datetime import datetime
from lxml import etree

API_KEY = ''
PLEX_HOST = ''

EpisodeType = {
    'Episode': 1,
    'Credits': 2,
    'Special': 3,
    'Trailer': 4,
    'Parody': 5,
    'Other': 6
}

#this is from https://github.com/plexinc-agents/PlexThemeMusic.bundle/blob/master/Contents/Code/__init__.py
THEME_URL = 'http://tvthemes.plexapp.com/%s.mp3'
LINK_REGEX = r"https?:\/\/\w+.\w+(?:\/?\w+)? \[([^\]]+)\]"

def ValidatePrefs():
    pass


def Start():
    Log("Shoko metata agent started")
    HTTP.Headers['Accept'] = 'application/json'
    HTTP.CacheTime = 0.1 #cache, can you please go away, typically we will be requesting LOCALLY. HTTP.CacheTime
    ValidatePrefs()


def GetApiKey():
    global API_KEY

    if not API_KEY:
        data = json.dumps({
            'user': Prefs['Username'],
            'pass': Prefs['Password'] if Prefs['Password'] != None else '',
            'device': 'Shoko Metadata For Plex'
        })
        resp = HttpPost('api/auth', data)['apikey']
        Log.Debug("Got API KEY: %s" % resp)
        API_KEY = resp
        return resp

    return API_KEY


def HttpPost(url, postdata):
    myheaders = {'Content-Type': 'application/json'}
    return JSON.ObjectFromString(
        HTTP.Request('http://%s:%s/%s' % (Prefs['Hostname'], Prefs['Port'], url), headers=myheaders,
                     data=postdata).content)


def HttpReq(url, authenticate=True, retry=True):
    global API_KEY
    Log("Requesting: %s" % url)

    if authenticate:
        myheaders['apikey'] = GetApiKey()

    try:
        return JSON.ObjectFromString(
            HTTP.Request('http://%s:%s/%s' % (Prefs['Hostname'], Prefs['Port'], url), headers=myheaders).content)
    except Exception, e:
        if not retry:
            raise e

        API_KEY = ''
        return HttpReq(url, authenticate, False)
        


class ShokoCommonAgent:
    def Search(self, results, media, lang, manual, movie):
        name = ( media.title if movie else media.show )

        if movie:
            if media.filename:
                filename = urllib.unquote(media.filename)

                Log('Searching movie %s - %s' % (name, filename))

                # Get file data using filename
                # http://127.0.0.1:8111/api/v3/File/PathEndsWith/%5Bjoseole99%5D%20Clannad%20-%2001%20(1280x720%20Blu-ray%20H264)%20%5B8E128DF5%5D.mkv
                file_data = HttpReq('api/v3/File/PathEndsWith/%s' % filename)

                # Take the first file. As we are searching with both parent folder and filename, there should be only one result.
                if len(file_data) > 1:
                    Log('File search has more than 1 result. HOW DID YOU DO IT?')
                file_data = file_data[0]

                # Get series data
                series_id = file_data['SeriesIDs'][0]['SeriesID']['ID'] # Taking the first matching anime. Not supporting multi-anime linked files for now. eg. Those two Toradora/One Piece episodes
                series_data = {}
                series_data['shoko'] = HttpReq('api/v3/Series/%s' % series_id) # http://127.0.0.1:8111/api/v3/Series/24
                series_data['anidb'] = HttpReq('api/v3/Series/%s/AniDB' % series_id) # http://127.0.0.1:8111/api/v3/Series/24/AniDB

                # Get episode data
                ep_id = file_data['SeriesIDs'][0]['EpisodeIDs'][0]['ID'] # Taking the first
                ep_data = {}
                ep_data['anidb'] = HttpReq('api/v3/Episode/%s/AniDB' % ep_id) # http://127.0.0.1:8111/api/v3/Episode/212/AniDB

                # Make a dict of language -> title for all titles in anidb data
                ep_titles = {}
                for item in ep_data['anidb']['Titles']:
                    ep_titles[item['Language']] = item['Name']

                # Get episode title according to the preference
                title = None
                for lang in Prefs['EpisodeTitleLanguagePreference'].split(','):
                    lang = lang.strip()
                    title = ep_titles[lang.upper()]
                    if title is not None: break
                if title is None: title = ep_titles['EN'] # If not found, fallback to EN title
                full_title = series_data['shoko']['Name'] + ' - ' + title

                # Get year from air date
                air_date = try_get(ep_data['anidb'], 'AirDate', None)
                year = air_date.split('-')[0] if air_date is not None else None

                score = 100 if series_data['shoko']['Name'] == name else 85  # TODO: Improve this to respect synonyms./

                meta = MetadataSearchResult(str(ep_id), full_title, year, score, lang)
                results.Append(meta)

            else: # For manual searches

                Log('Searching movie %s' % name)

                # Search for series using the name
                prelimresults = HttpReq('api/v3/Series/Search/%s' % urllib.quote(name.encode('utf8'))) # http://127.0.0.1:8111/api/v3/Series/Search/Clannad

                for result in prelimresults:
                    # Get episode list using series ID
                    episodes = HttpReq('api/v3/Series/%s/Episode' % result['IDs']['ID']) # http://127.0.0.1:8111/api/v3/Series/212/Episode

                    for episode in episodes:
                        # Get episode data
                        ep_id = episode['IDs']['ID']
                        ep_data = {}
                        ep_data['anidb'] = HttpReq('api/v3/Episode/%s/AniDB' % ep_id) # http://127.0.0.1:8111/api/v3/Episode/212/AniDB

                        # Get series data
                        series_data = {}
                        series_data['shoko'] = HttpReq('api/v3/Episode/%s/Series' % ep_id) # http://127.0.0.1:8111/api/v3/Episode/212/Series

                        # Make a dict of language -> title for all titles in anidb data
                        ep_titles = {}
                        for item in ep_data['anidb']['Titles']:
                            ep_titles[item['Language']] = item['Name']

                        # Get episode title according to the preference
                        title = None
                        for lang in Prefs['EpisodeTitleLanguagePreference'].split(','):
                            lang = lang.strip()
                            title = ep_titles[lang.upper()]
                            if title is not None: break
                        if title is None: title = ep_titles['EN'] # If not found, fallback to EN title
                        full_title = series_data['shoko']['Name'] + ' - ' + title

                        # Get year from air date
                        air_date = try_get(ep_data['anidb'], 'AirDate', None)
                        year = air_date.split('-')[0] if air_date is not None else None

                        if title == name: score = 100 # Check if full name matches (Series name + episode name)
                        elif result['Name'] == name: score = 90 # Check if series name matches
                        else: score = 80

                        meta = MetadataSearchResult(str(ep_id), full_title, year, score, lang)
                        results.Append(meta)

        else:
            # Search for series using the name
            prelimresults = HttpReq('api/v3/Series/Search/%s' % urllib.quote(name.encode('utf8'))) # http://127.0.0.1:8111/api/v3/Series/Search/Clannad

            for result in prelimresults:
                # Get series data
                series_id = result['IDs']['ID']
                series_data = {}
                series_data['shoko'] = result # Just to make it uniform across every place it's used
                series_data['anidb'] = HttpReq('api/v3/Series/%s/AniDB' % series_id)

                # Get year from air date
                air_date = try_get(series_data['anidb'], 'AirDate', None)
                year = air_date.split('-')[0] if air_date is not None else None

                score = 100 if series_data['shoko']['Name'] == name else 85  # TODO: Improve this to respect synonyms./

                meta = MetadataSearchResult(str(series_id), series_data['shoko']['Name'], year, score, lang)
                results.Append(meta)

                # results.Sort('score', descending=True)

    def Update(self, metadata, media, lang, force, movie):
        Log("update(%s)" % metadata.id)
        aid = metadata.id

        flags = 0
        flags = flags | Prefs['hideMiscTags']       << 0 #0b00001 : Hide AniDB Internal Tags
        flags = flags | Prefs['hideArtTags']        << 1 #0b00010 : Hide Art Style Tags
        flags = flags | Prefs['hideSourceTags']     << 2 #0b00100 : Hide Source Work Tags
        flags = flags | Prefs['hideUsefulMiscTags'] << 3 #0b01000 : Hide Useful Miscellaneous Tags
        flags = flags | Prefs['hideSpoilerTags']    << 4 #0b10000 : Hide Plot Spoiler Tags

        if movie:
            # Get series data
            series_data = {}
            series_data['shoko'] = HttpReq('api/v3/Episode/%s/Series' % aid) # http://127.0.0.1:8111/api/v3/Series/24
            series_id = series_data['shoko']['IDs']['ID']
            series_data['anidb'] = HttpReq('api/v3/Series/%s/AniDB' % series_id) # http://127.0.0.1:8111/api/v3/Series/24/AniDB

            # Get episode data
            ep_data = {}
            ep_data['anidb'] = HttpReq('api/v3/Episode/%s/AniDB' % (aid)) # http://127.0.0.1:8111/api/v3/Episode/212/AniDB

            aid = series_id # Change aid to series ID

            # Make a dict of language -> title for all titles in anidb data
            ep_titles = {}
            for item in ep_data['anidb']['Titles']:
                ep_titles[item['Language']] = item['Name']

            title = try_get(ep_titles, 'EN', None)
            if title in ['Complete Movie', 'Web']:
                movie_name = series_data['anidb']['Name']
                movie_sort_name = series_data['anidb']['Name']
            else:
                # Get episode title according to the preference
                title = None
                for lang in Prefs['EpisodeTitleLanguagePreference'].split(','):
                    lang = lang.strip()
                    title = ep_titles[lang.upper()]
                    if title is not None: break
                if title is None: title = ep_titles['EN'] # If not found, fallback to EN title
                movie_name = series_data['shoko']['Name'] + ' - ' + title
                movie_sort_name = series_data['shoko']['Name'] + ' - ' + str(ep_data['anidb']['EpisodeNumber']).zfill(3)

            Log('Movie Title: %s' % movie_name)

            metadata.summary = summary_sanitizer(try_get(series_data['anidb'], 'Description'))
            metadata.title = movie_name
            metadata.title_sort = movie_sort_name
            metadata.rating = float(ep_data['anidb']['Rating']['Value']/100)
            
            # Get year from air date
            air_date = try_get(ep_data['anidb'], 'AirDate', None)
            year = air_date.split('-')[0] if air_date is not None else None

            if year:
                metadata.year = int(year)

            if air_date is not None:
                metadata.originally_available_at = datetime.strptime(air_date, '%Y-%m-%d').date()

        else:
            # Get series data
            series_data = {}
            series_data['shoko'] = HttpReq('api/v3/Series/%s' % aid) # http://127.0.0.1:8111/api/v3/Series/24
            series_data['anidb'] = HttpReq('api/v3/Series/%s/AniDB' % aid) # http://127.0.0.1:8111/api/v3/Series/24/AniDB

            Log('Series Title: %s' % series_data['shoko']['Name'])

            metadata.summary = summary_sanitizer(try_get(series_data['anidb'], 'Description'))
            metadata.title = series_data['shoko']['Name']
            metadata.rating = float(series_data['anidb']['Rating']['Value']/100)

            # Get air date
            air_date = try_get(series_data['anidb'], 'AirDate', None)
            if air_date is not None:
                metadata.originally_available_at = datetime.strptime(air_date, '%Y-%m-%d').date()

        # Get series tags
        series_tags = HttpReq('api/v3/Series/%s/Tags/%d' % (aid, flags)) # http://127.0.0.1:8111/api/v3/Series/24/Tags/0
        tags = [tag['Name'] for tag in series_tags]
        metadata.genres = tags

        # Get images
        images = try_get(series_data['shoko'], 'Images', {})
        self.metadata_add(metadata.banners, try_get(images, 'Banners', []))
        self.metadata_add(metadata.posters, try_get(images, 'Posters', []))
        self.metadata_add(metadata.art, try_get(images, 'Fanarts', []))

        # Get group
        groupinfo = HttpReq('api/v3/Series/%s/Group' % aid)
        metadata.collections = [groupinfo['Name']] if groupinfo['Size'] > 1 else []


        ### Generate general content ratings.
        ### VERY rough approximation to: https://www.healthychildren.org/English/family-life/Media/Pages/TV-Ratings-A-Guide-for-Parents.aspx

        if Prefs["Ratings"]:
            if 'Kodomo' in tags:
                metadata.content_rating = 'TV-Y'

            if 'Mina' in tags:
                metadata.content_rating = 'TV-G'

            if 'Shoujo' in tags:
                metadata.content_rating = 'TV-14'

            if 'Shounen' in tags:
                metadata.content_rating = 'TV-14'

            if 'Josei' in tags:
                metadata.content_rating = 'TV-14'

            if 'Seinen' in tags:
                metadata.content_rating = 'TV-MA'

            if 'Mature' in tags:
                metadata.content_rating = 'TV-MA'

            if '18 Restricted' in tags:
                metadata.content_rating = 'TV-R'

            Log('Assumed tv rating to be: %s' % metadata.content_rating)

        # Get cast
        cast = HttpReq('api/v3/Series/%s/Cast' % aid) # http://127.0.0.1:8111/api/v3/Series/24/Cast
        metadata.roles.clear()
        Log('Cast')
        for role in cast:
            meta_role = metadata.roles.new()
            meta_role.name = role['Staff']['Name']
            meta_role.role = role['Character']['Name']
            Log('%s - %s' % (meta_role.role, meta_role.name))
            image = role['Staff']['Image']
            meta_role.photo = 'http://{host}:{port}/api/v3/Image/{source}/{type}/{id}'.format(host=Prefs['Hostname'], port=Prefs['Port'], source=image['Source'], type=image['Type'], id=image['ID'])


        if not movie:
            # Get episode list using series ID
            episodes = HttpReq('api/v3/Series/%s/Episode' % aid) # http://127.0.0.1:8111/api/v3/Series/212/Episode

            for episode in episodes:
                # Get episode data
                ep_id = episode['IDs']['ID']
                ep_data = {}
                ep_data['anidb'] = HttpReq('api/v3/Episode/%s/AniDB' % ep_id)
                ep_data['tvdb'] = HttpReq('api/v3/Episode/%s/TvDB' % ep_id)

                ep_type = ep_data['anidb']['Type']
                if ep_type not in [1, 3, 2, 4]: # Episode, Special, Credits, Trailer
                    continue

                # Get season number
                season = 0
                if ep_type == EpisodeType['Episode']: season = 1
                elif ep_type == EpisodeType['Special']: season = 0
                elif ep_type == EpisodeType['Credits']: season = -1
                elif ep_type == EpisodeType['Trailer']: season = -2
                if not Prefs['SingleSeasonOrdering'] and len(ep_data['tvdb']) != 0:
                    ep_data['tvdb'] = ep_data['tvdb'][0] # Take the first link, as explained before
                    season = ep_data['tvdb']['Season']
                    if season <= 0 and ep_type == EpisodeType['Episode']: season = 1
                    elif season > 0 and ep_type == EpisodeType['Special']: season = 0

                Log('Season: %s', season)
                Log('Episode: %s', ep_data['anidb']['EpisodeNumber'])

                episode_obj = metadata.seasons[season].episodes[ep_data['anidb']['EpisodeNumber']]

                # Make a dict of language -> title for all titles in anidb data
                ep_titles = {}
                for item in ep_data['anidb']['Titles']:
                    ep_titles[item['Language']] = item['Name']

                # Get episode title according to the preference
                title = None
                for lang in Prefs['EpisodeTitleLanguagePreference'].split(','):
                    lang = lang.strip()
                    title = ep_titles[lang.upper()]
                    if title is not None: break
                if title is None: title = ep_titles['EN'] # If not found, fallback to EN title
                episode_obj.title = title

                Log('Episode Title: %s', episode_obj.title)

                # Get description
                if try_get(ep_data['anidb'], 'Description') != 'Episode Overview not Available':
                    episode_obj.summary = summary_sanitizer(try_get(ep_data['anidb'], 'Description'))
                    Log('Description: %s' % episode_obj.summary)

                # Get air date
                air_date = try_get(ep_data['anidb'], 'AirDate', None)
                if air_date is not None:
                    episode_obj.originally_available_at = datetime.strptime(air_date, '%Y-%m-%d').date()

                if Prefs['customThumbs'] and 'Thumbnail' in ep_data['tvdb']:
                   self.metadata_add(episode_obj.thumbs, [ep_data['tvdb']['Thumbnail']])

            #adapted from: https://github.com/plexinc-agents/PlexThemeMusic.bundle/blob/fb5c77a60c925dcfd60e75a945244e07ee009e7c/Contents/Code/__init__.py#L41-L45
            if Prefs["themeMusic"]:
                for tid in try_get(series_data['shoko']['IDs'],'TvDB', []):
                    if THEME_URL % tid not in metadata.themes:
                        try:
                            metadata.themes[THEME_URL % tid] = Proxy.Media(HTTP.Request(THEME_URL % tid))
                            Log("added: %s" % THEME_URL % tid)
                        except:
                            Log("error adding music, probably not found")

    def metadata_add(self, meta, images):
        valid = list()
        
        art_url = '' # Declaring it inside the loop throws UnboundLocalError for some reason
        for art in images:
            try:
                art_url = '/api/v3/Image/{source}/{type}/{id}'.format(source=art['Source'], type=art['Type'], id=art['ID'])
                url = 'http://{host}:{port}{relativeURL}'.format(host=Prefs['Hostname'], port=Prefs['Port'], relativeURL=art_url)
                idx = try_get(art, 'index', 0)
                Log("[metadata_add] :: Adding metadata %s (index %d)" % (url, idx))
                meta[art['url']] = Proxy.Media(HTTP.Request(url).content, idx)
                valid.append(art['url'])
            except Exception as e:
                Log("[metadata_add] :: Invalid URL given (%s), skipping" % art['url'])
                Log(e)

        meta.validate_keys(valid)

        for key in meta.keys():
            if (key not in valid):
                del meta[key]

def summary_sanitizer(summary):
    if Prefs["synposisCleanLinks"]:
        summary = re.sub(LINK_REGEX, r'\1', summary)                                           # Replace links
    if Prefs["synposisCleanMiscLines"]:
        summary = re.sub(r'^(\*|--|~) .*',              "",      summary, flags=re.MULTILINE)  # Remove the line if it starts with ('* ' / '-- ' / '~ ')
    if Prefs["synposisRemoveSummary"]:
        summary = re.sub(r'\n(Source|Note|Summary):.*', "",      summary, flags=re.DOTALL)     # Remove all lines after this is seen
    if Prefs["synposisCleanMultiEmptyLines"]:
        summary = re.sub(r'\n\n+',                      r'\n\n', summary, flags=re.DOTALL)     # Condense multiple empty lines
    return summary.strip(" \n")

def try_get(arr, idx, default=""):
    try:
        return arr[idx]
    except:
        return default


class ShokoTVAgent(Agent.TV_Shows, ShokoCommonAgent):
    name, primary_provider, fallback_agent, contributes_to, accepts_from = (
        'ShokoTV', True, False, ['com.plexapp.agents.hama'],
        ['com.plexapp.agents.localmedia'])  # , 'com.plexapp.agents.opensubtitles'
    languages = [Locale.Language.English, 'fr', 'zh', 'sv', 'no', 'da', 'fi', 'nl', 'de', 'it', 'es', 'pl', 'hu', 'el',
                 'tr', 'ru', 'he', 'ja', 'pt', 'cs', 'ko', 'sl', 'hr']

    def search(self, results, media, lang, manual): self.Search(results, media, lang, manual, False)

    def update(self, metadata, media, lang, force): self.Update(metadata, media, lang, force, False)


class ShokoMovieAgent(Agent.Movies, ShokoCommonAgent):
    name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = (
        'ShokoMovies', True, False, ['com.plexapp.agents.hama'], [Locale.Language.English, 'fr', 'zh', 'sv', 'no', 'da', 'fi', 'nl', 'de', 'it', 'es', 'pl', 'hu', 'el', 'tr', 'ru', 'he', 'ja', 'pt', 'cs', 'ko', 'sl', 'hr'],
        ['com.plexapp.agents.localmedia'])  # , 'com.plexapp.agents.opensubtitles'

    def search(self, results, media, lang, manual): self.Search(results, media, lang, manual, True)

    def update(self, metadata, media, lang, force): self.Update(metadata, media, lang, force, True)
