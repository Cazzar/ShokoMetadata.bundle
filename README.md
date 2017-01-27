ShokoMetadata.bundle
====================
This is a plex library metadata currently written **only** for TV shows.

Usage:
Until japanesemediamanager/ShokoServer#546 is merged matching will not be 100%

## Notes
Naming episodes/series works best with [This format](https://support.plex.tv/hc/en-us/articles/200220687-Naming-Series-Season-Based-TV-Shows)

Though Some defaults from Shoko do work, personally, I use:

**disclaimer:**: this doesn't work 100% I am working alongside the Shoko devs for better naming support.

```
// Sample Output: [Coalgirls]_Highschool_of_the_Dead_-_01_(1920x1080_Blu-ray_H264)_[90CC6DC1].mkv
// Sub group name
IF G(!) DO ADD '[%grp] '
// Anime Name, use english name if it exists, otherwise use the Romaji name
IF I(eng) DO ADD '%eng '
IF I(ann);I(!eng) DO ADD '%ann '
// Episode Number, don't use episode number for movies
IF T(!Movie) DO ADD '- %enr'
// If the file version is v2 or higher add it here
IF F(!1) DO ADD 'v%ver'
// Video Resolution
DO ADD ' (%res'
// Video Source (only if blu-ray or DVD)
IF R(DVD),R(Blu-ray) DO ADD ' %src'
// Video Codec
DO ADD ' %vid'
// Video Bit Depth (only if 10bit)
IF Z(10) DO ADD ' %bitbit'
DO ADD ') '
DO ADD '[%CRC]'

// Replacement rules (cleanup)
//DO REPLACE ' ' '_' // replace spaces with underscores
DO REPLACE 'H264/AVC' 'H264'
DO REPLACE '0x0' ''
DO REPLACE '__' '_'
DO REPLACE '__' '_'

// Replace all illegal file name characters
DO REPLACE '<' '('
DO REPLACE '>' ')'
DO REPLACE ':' '-'
DO REPLACE '"' '`'
DO REPLACE '/' '_'
DO REPLACE '/' '_'
DO REPLACE '\' '_'
DO REPLACE '|' '_'
DO REPLACE '?' '_'
DO REPLACE '*' '_'
```

# Plans

I do plan to in the long term to add things such as scrobbling to this plugin

Another future plan is in regards to syncing watched status between shoko and plex.
