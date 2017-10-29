import re, os, os.path, json
import Media, VideoFiles, Stack, Utils

import urllib2, urllib

Prefs = {
    'Hostname': '192.168.1.3',
    'Port': 8111,
    'Username': 'Default',
    'Password': '',
    'IncludeOther': True
}

API_KEY = ''

def log(methodName, message, *args):
    '''
        Create a log message given the message and arguments
    '''
    logMsg = message
    # Replace the arguments in the string
    if args:
        logMsg = message % args
        
    logMsg = methodName + ' :: ' + logMsg
    print logMsg


def HttpPost(url, postdata):
    myheaders = {'Content-Type': 'application/json'}
    
    req = urllib2.Request('http://%s:%s/%s' % (Prefs['Hostname'], Prefs['Port'], url), headers=myheaders)
    return json.load(urllib2.urlopen(req, postdata))


def HttpReq(url, authenticate=True):
    log('HttpReq' ,"Requesting: %s", url)
    api_string = ''
    if authenticate:
        api_string = '&apikey=%s' % GetApiKey()

    myheaders = {'Accept': 'application/json'}
    
    req = urllib2.Request('http://%s:%s/%s%s' % (Prefs['Hostname'], Prefs['Port'], url, api_string), headers=myheaders)
    return json.load(urllib2.urlopen(req))


def GetApiKey():
    global API_KEY

    if not API_KEY:
        data = '{"user":"%s", "pass":"%s", "device":"%s"}' % (
            Prefs['Username'], Prefs['Password'] if Prefs['Password'] != None else '', 'Shoko Series Scanner For Plex')
        resp = HttpPost('api/auth', data)['apikey']
        log('GetApiKey', "Got API KEY: %s", resp)
        API_KEY = resp
        return resp

    return API_KEY


def Scan(path, files, mediaList, subdirs, language=None, root=None):
    log('Scan', 'path: %s', path)
    log('Scan', 'files: %s', files)
    log('Scan', 'mediaList: %s', mediaList)
    log('Scan', 'subdirs: %s', subdirs)
    log('Scan', 'language: %s', language)
    log('Scan', 'root: %s', root)
    
    # Scan for video files.
    VideoFiles.Scan(path, files, mediaList, subdirs, root)
    
    for idx, file in enumerate(files):
        log('Scan', 'file: %s', file)
        # http://127.0.0.1:8111/api/ep/getbyfilename?apikey=d422dfd2-bdc3-4219-b3bb-08b85aa65579&filename=%5Bjoseole99%5D%20Clannad%20-%2001%20(1280x720%20Blu-ray%20H264)%20%5B8E128DF5%5D.mkv

        episode_data = HttpReq("api/ep/getbyfilename?filename=%s" % (urllib.quote(os.path.basename(file))))
        if len(episode_data) == 0: break
        if (try_get(episode_data, "code", 200) == 404): break

        series_data = HttpReq("api/serie/fromep?id=%d&nocast=1&notag=1" % episode_data['id'])
        if (series_data["ismovie"] == 0):
            continue 
        showTitle = series_data['name'].encode("utf-8") #no idea why I need to do this.
        log('Scan', 'show title: %s', showTitle)

        seasonYear = episode_data['year']
        log('Scan', 'season year: %s', seasonYear)

        vid = Media.Movie(showTitle, int(seasonYear))
        log('Scan', 'vid: %s', vid)
        vid.parts.append(file)
        mediaList.append(vid)
    
    log('Scan', 'stack media')
    Stack.Scan(path, files, mediaList, subdirs)
    log('Scan', 'media list %s', mediaList)


def try_get(arr, idx, default=""):
    try:
        return arr[idx]
    except:
        return default