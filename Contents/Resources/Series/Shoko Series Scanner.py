import re, os, os.path, json
import Media, VideoFiles, Stack, Utils

import urllib2, urllib

Prefs = {
    'Hostname': '127.0.0.1',
    'Port': 8111,
    'Username': 'Default',
    'Password': '',
    'IncludeSpecials': True,
    'IncludeOther': False,
    'SingleSeasonOrdering': False
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


def HttpReq(url, retry=True):
    global API_KEY
    Log.info("Requesting: %s", url)

    myheaders = {'Accept': 'application/json', 'apikey': GetApiKey()}
    
    try:
        req = urllib2.Request('http://%s:%s/%s' % (Prefs['Hostname'], Prefs['Port'], url), headers=myheaders)
        return json.load(urllib2.urlopen(req))
    except Exception, e:
        if not retry:
            raise e

        API_KEY = ''
        return HttpReq(url, False)


def GetApiKey():
    global API_KEY

    if not API_KEY:
        data = json.dumps({
            'user': Prefs['Username'],
            'pass': Prefs['Password'] if Prefs['Password'] != None else '',
            'device': 'Shoko Series Scanner For Plex'
        })
        resp = HttpPost('api/auth', data)['apikey']
        Log.info( "Got API KEY: %s", resp)
        API_KEY = resp
        return resp

    return API_KEY


def Scan(path, files, mediaList, subdirs, language=None, root=None):
    Log.debug('path: %s', path)
    Log.debug('files: %s', files)

    for subdir in subdirs:
        Log.info("[folder] " + os.path.relpath(subdir, root))

    if files:
        
        # Scan for video files.
        VideoFiles.Scan(path, files, mediaList, subdirs, root)
        
        for idx, file in enumerate(files):
            try:
                Log.info('file: %s', file)

                # Get file data using filename
                # http://127.0.0.1:8111/api/v3/File/PathEndsWith/Clannad/%5Bjoseole99%5D%20Clannad%20-%2001%20(1280x720%20Blu-ray%20H264)%20%5B8E128DF5%5D.mkv
                filename = os.path.join(os.path.split(os.path.dirname(file))[-1], os.path.basename(file)) # Parent folder + file name
                file_data = HttpReq('api/v3/File/PathEndsWith/%s' % (urllib.quote(filename)))
                if len(file_data) == 0: continue # Skip if file data is not found

                # Take the first file. As we are searching with both parent folder and filename, there should be only one result.
                if len(file_data) > 1:
                    Log.info('File search has more than 1 result. HOW DID YOU DO IT?')
                    Log.info('Unsupported! Skipping...')
                    continue

                file_data = file_data[0]
                
                # Ignore unrecognized files
                if 'SeriesIDs' not in file_data or file_data['SeriesIDs'] is None:
                    Log.info('Unrecognized file. Skipping!')
                    continue

                # Get series data
                series_ids = try_get(file_data['SeriesIDs'], 0, None)

                if series_ids is None:
                    Log.info('Unrecognized file. Skipping!')
                    continue

                series_id = series_ids['SeriesID']['ID'] # Taking the first matching anime. Not supporting multi-anime linked files for now. eg. Those two Toriko/One Piece episodes
                series_data = HttpReq('api/v3/Series/%s?includeDataFrom=AniDB' % series_id) # http://127.0.0.1:8111/api/v3/Series/24?includeDataFrom=AniDB

                # Get preferred/overridden title. Preferred title is the one shown in Desktop.
                show_title = series_data['Name'].encode('utf-8') #no idea why I need to do this.
                Log.info('Show Title: %s', show_title)

                # Get episode data
                episode_multi = len(file_data['SeriesIDs'][0]['EpisodeIDs']) # Account for multi episode files
                for episode in range(episode_multi):
                    episode_id = file_data['SeriesIDs'][0]['EpisodeIDs'][episode]['ID']
                    episode_data = HttpReq('api/v3/Episode/%s?includeDataFrom=AniDB,TvDB' % episode_id) # http://127.0.0.1:8111/api/v3/Episode/212/AniDB?includeDataFrom=AniDB,TvDB
                    
                    # Get episode type
                    episode_type = episode_data['AniDB']['Type']

                    # Ignore multi episode files of differing types (anidb episode relations)
                    if episode > 0 and episode_type != episode_data['AniDB']['Type']: continue

                    # Get season number
                    season = 0
                    if episode_type == 'Normal': season = 1
                    elif episode_type == 'Special': season = 0
                    elif episode_type == 'ThemeSong': season = -1
                    elif episode_type == 'Trailer': season = -2
                    elif episode_type == 'Parody': season = -3
                    elif episode_type == 'Unknown': season = -4
                    if not Prefs['SingleSeasonOrdering']:
                        episode_data['TvDB'] = try_get(episode_data['TvDB'], 0, None) # Take the first link, as explained before
                        if episode_data['TvDB'] is not None:
                            season = episode_data['TvDB']['Season']

                    # Ignore these by choice.
                    if season == 0 and Prefs['IncludeSpecials'] == False: continue
                    if season < 0 and Prefs['IncludeOther'] == False: continue

                    # Ignore movies in preference for Shoko Movie Scanner, but keep specials as Plex sees specials as duplicate
                    if (try_get(series_data['AniDB'], 'Type', 'Unknown') == 'Movie' and season >= 1 and Prefs['CombineSeriesAndMovies'] == False):
                        Log.info('It\'s a movie. Skipping!')
                        continue

                    Log.info('Season: %s', season)

                    if not Prefs['SingleSeasonOrdering'] and episode_data['TvDB'] is not None:
                        episode_number = episode_data['TvDB']['Number']
                    else:
                        episode_number = episode_data['AniDB']['EpisodeNumber']

                    Log.info('Episode Number: %s', episode_number)

                    vid = Media.Episode(show_title, season, episode_number)
                    if episode_multi > 1: vid.display_offset = (episode * 100) / episode_multi # required for multi episode files
                    Log.info('vid: %s', vid)
                    vid.parts.append(file)
                    mediaList.append(vid)
            except Exception as e:
                Log.error("Error in Scan: '%s'" % e)
                continue

        Stack.Scan(path, files, mediaList, subdirs)

    if not path: # If current folder is root folder
        Log.info("Manual call to group folders")
        subfolders = subdirs[:]

        while subfolders: # subfolder scanning queue
            full_path = subfolders.pop(0)
            path = os.path.relpath(full_path, root)

            reverse_path = list(reversed(path.split(os.sep)))
            
            Log.info('=' * 100)
            Log.info('Started subfolder scan: %s', full_path)
            Log.info('=' * 100)

            subdir_dirs, subdir_files = [], []

            for file in os.listdir(full_path):
                path_item = os.path.join(full_path, file) 
                if os.path.isdir(path_item):
                    subdir_dirs.append(path_item)
                else:
                    subdir_files.append(path_item)

            Log.info("Sub-directories: %s", subdir_dirs)
            Log.info("Files: %s", subdir_files)

            for dir in subdir_dirs:
                Log.info("[Added for scanning] " + dir) # Add the subfolder to subfolder scanning queue)
                subfolders.append(dir)

            grouping_dir = full_path.rsplit(os.sep, full_path.count(os.sep)-1-root.count(os.sep))[0]
            if subdir_files and (len(reverse_path)>1 or subdir_dirs):
                if grouping_dir in subdirs:
                    subdirs.remove(grouping_dir)  #Prevent group folders from being called by Plex normal call to Scan()
                Log.info("CALLING SCAN FOR FILES IN CURRENT FOLDER")
                Scan(path, sorted(subdir_files), mediaList, [], language, root) 
                # relative path for dir or it will group multiple series into one as before and no empty subdirs array because they will be scanned afterwards.
            
            Log.info('=' * 100)
            Log.info('Completed subfolder scan: %s', full_path)
            Log.info('=' * 100)


def try_get(arr, idx, default=""):
    try:
        return arr[idx]
    except:
        return default
