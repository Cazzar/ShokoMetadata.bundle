import re, os, os.path, json
import Media, VideoFiles, Stack, Utils

import urllib2, urllib

Prefs = {
    'Hostname': '127.0.0.1',
    'Port': 8111,
    'Username': 'Default',
    'Password': '',
    'IncludeOther': True
}

API_KEY = ''

### Log + LOG_PATH calculated once for all calls ###
import logging, logging.handlers                        #
RootLogger     = logging.getLogger('main')
RootHandler    = None
RootFormatting = logging.Formatter('%(message)s') #%(asctime)-15s %(levelname)s -
RootLogger.setLevel(logging.DEBUG)
Log             = RootLogger

FileListLogger     = logging.getLogger('FileListLogger')
FileListHandler    = None
FileListFormatting = logging.Formatter('%(message)s')
FileListLogger.setLevel(logging.DEBUG)
LogFileList = FileListLogger.info

def set_logging(instance, filename):
  global RootLogger, RootHandler, RootFormatting, FileListLogger, FileListHandler, FileListFormatting
  logger, handler, formatting, backup_count = [RootLogger, RootHandler, RootFormatting, 9] if instance=="Root" else [FileListLogger, FileListHandler, FileListFormatting, 1]
  if handler: logger.removeHandler(handler)
  handler = logging.handlers.RotatingFileHandler(os.path.join(LOG_PATH, filename), maxBytes=10*1024*1024, backupCount=backup_count)    #handler = logging.FileHandler(os.path.join(LOG_PATH, filename), mode)
  #handler.setFormatter(formatting)
  handler.setLevel(logging.DEBUG)
  logger.addHandler(handler)
  if instance=="Root":  RootHandler     = handler
  else:                 FileListHandler = handler

### Check config files on boot up then create library variables ###    #platform = xxx if callable(getattr(sys,'platform')) else ""
import inspect
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), "..", "..", "Logs"))
if not os.path.isdir(LOG_PATH):
  path_location = { 'Windows': '%LOCALAPPDATA%\\Plex Media Server',
                    'MacOSX':  '$HOME/Library/Application Support/Plex Media Server',
                    'Linux':   '$PLEX_HOME/Library/Application Support/Plex Media Server' }
  try:  path = os.path.expandvars(path_location[Platform.OS.lower()] if Platform.OS.lower() in path_location else '~')  # Platform.OS:  Windows, MacOSX, or Linux
  except: pass #os.makedirs(LOG_PATH)  # User folder on MacOS-X
LOG_FILE_LIBRARY = LOG_FILE = 'Shoko Metadata Scanner.log'                # Log filename library will include the library name, LOG_FILE not and serve as reference
set_logging("Root", LOG_FILE_LIBRARY)


def HttpPost(url, postdata):
    myheaders = {'Content-Type': 'application/json'}
    
    req = urllib2.Request('http://%s:%s/%s' % (Prefs['Hostname'], Prefs['Port'], url), headers=myheaders)
    return json.load(urllib2.urlopen(req, postdata))


def HttpReq(url, authenticate=True, retry=True):
    global API_KEY
    Log.info("Requesting: %s", url)
    api_string = ''
    if authenticate:
        api_string = '&apikey=%s' % GetApiKey()

    myheaders = {'Accept': 'application/json'}
    
    try:
        req = urllib2.Request('http://%s:%s/%s%s' % (Prefs['Hostname'], Prefs['Port'], url, api_string), headers=myheaders)
        return json.load(urllib2.urlopen(req))
    except Exception, e:
        if not retry:
            raise e

        API_KEY = ''
        return HttpReq(url, authenticate, False)


def GetApiKey():
    global API_KEY

    if not API_KEY:
        data = '{"user":"%s", "pass":"%s", "device":"%s"}' % (
            Prefs['Username'], Prefs['Password'] if Prefs['Password'] != None else '', 'Shoko Series Scanner For Plex')
        resp = HttpPost('api/auth', data)['apikey']
        Log.info( "Got API KEY: %s", resp)
        API_KEY = resp
        return resp

    return API_KEY


def Scan(path, files, mediaList, subdirs, language=None, root=None):
    try:
        Log.debug('path: %s', path)
        Log.debug('files: %s', files)
        Log.debug('mediaList: %s', mediaList)
        Log.debug('subdirs: %s', subdirs)
        Log.debug('language: %s', language)
        Log.info('root: %s', root)
        
        # Scan for video files.
        VideoFiles.Scan(path, files, mediaList, subdirs, root)
        
        for idx, file in enumerate(files):
            Log.info('file: %s', file)
            # http://127.0.0.1:8111/api/ep/getbyfilename?apikey=d422dfd2-bdc3-4219-b3bb-08b85aa65579&filename=%5Bjoseole99%5D%20Clannad%20-%2001%20(1280x720%20Blu-ray%20H264)%20%5B8E128DF5%5D.mkv

            episode_data = HttpReq("api/ep/getbyfilename?filename=%s" % (urllib.quote(os.path.basename(file))))
            if len(episode_data) == 0: break
            if (try_get(episode_data, "code", 200) == 404): break

            series_data = HttpReq("api/serie/fromep?id=%d&nocast=1&notag=1" % episode_data['id'])
            if (series_data["ismovie"] == 1): break # Ignore movies in preference for Shoko Movie Scanner
            showTitle = series_data['name'].encode("utf-8") #no idea why I need to do this.
            Log.info('show title: %s', showTitle)

            seasonNumber = 0
            seasonStr = try_get(episode_data, 'season', None)
            if seasonStr == None:
                if episode_data['eptype'] == 'Episode': seasonNumber = 1
                if episode_data['eptype'] == 'Credits': seasonNumber = -1 #season -1 for OP/ED
            else:
                seasonNumber = seasonStr.split('x')[0]

            if seasonNumber <= 0 and Prefs['IncludeOther'] == False: break #Ignore this by choice.
                

            Log.info('season number: %s', seasonNumber)
            episodeNumber = int(episode_data['epnumber'])
            Log.info('episode number: %s', episodeNumber)

            vid = Media.Episode(showTitle, int(seasonNumber), episodeNumber)
            Log.info('vid: %s', vid)
            vid.parts.append(file)
            mediaList.append(vid)
        
        Log.info('stack media')
        Stack.Scan(path, files, mediaList, subdirs)
        Log.debug('media list %s', mediaList)
    except Exception as e:
        Log.error("Error in Scan: '%s'" % e)


def try_get(arr, idx, default=""):
    try:
        return arr[idx]
    except:
        return default
