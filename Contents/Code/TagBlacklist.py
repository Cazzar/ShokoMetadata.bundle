# Comment any you don't believe should be in here or create an ongoing issue for discussion
# Some are in here as they are folders, with only recursive anime belonging to them (those will have more specific tags)
tagBlacklistAniDBHelpers = [
    "body and host",
    "breasts",
    "broadcast cropped to 4-3",
    "cast missing",
    "cast",
    "content indicators",
    "delayed 16-9 broadcast",
    "description missing",
    "development hell",  # :( God Eater
    "dialogue driven",  # anidb and their british spellings
    "dynamic",
    "earth",
    "elements",
    "ending",
    "ensemble cast",
    "family life",
    "fast-paced",
    "fictional world",
    "full hd version available",
    "jdrama adaptation",
    "meta tags",
    "motifs",
    "multi-anime projects",
    "noitamina",
    "origin",
    "past",
    "place",
    "present",
    "season",
    "sentai",
    "setting",
    "some weird shit goin` on",  # these are some grave accents in use...
    "storytelling",
    "tales",
    "target audience",
    "technical aspects",
    "television programme",
    "themes",
    "time",
    "translation convention",
    "tropes",
    "ungrouped",
    "unsorted"
]

tagBlackListSource = [
    "4-koma",
    "action game",
    "erotic game",
    "fan-made",
    "game",
    "korean drama",
    "manga",
    "manhua",
    "manhwa",
    "movie",
    "new",
    "novel",
    "radio programme",
    "remake",
    "rpg",
    "television programme",
    "ultra jump",
    "visual novel"
]

tagBlackListArtStyle = [
    "3d cg animation",
    "3d cg closing",
    "cel-shaded animation",
    "cgi",
    "chibi ed",
    "experimental animation",
    "flash animation",
    "live-action closing",
    "live-action imagery",
    "off-model animation",
    "photographic backgrounds",
    "product placement",
    "recycled animation",
    "slide show animation",
    "thick line animation",
    "vignette scenes",
    "watercolour style",
    "widescreen transition"
]

tagBlackListUsefulHelpers = [
    "ed variety",
    "half-length episodes",
    "long episodes",
    "multi-segment episodes",
    "op and ed sung by characters",
    "op variety",
    "post-credits scene",
    "recap in opening",
    "short episodes",
    "short movie",
    "stand-alone movie",
    "subtle op ed sequence change"
]

tagBlackListPlotSpoilers = [
    "branching story",
    "cliffhangers",
    "colour coded",
    "complex storyline",
    "drastic change in sequel",
    "fillers",
    "first girl wins",  # seriously a spoiler
    "incomplete story",
    "inconclusive",
    "inconclusive romantic plot",
    "non-linear",
    "open-ended",
    "room for sequel",
    "sudden change of pace",
    "tone changes",
    "unresolved",
    "unresolved romance"
]


# Feed this a list of str types
def processTags(string):
    to_remove = []
    remove_original = False

    for a in string:
        tag = str(a).lower().strip()
        if Prefs['hideArtTags']:
            for remove in tagBlackListArtStyle:
                if remove == tag:
                    to_remove.append(a)
                    break
            if "censor" in tag:
                to_remove.append(a)
        if Prefs['hideSourceTags']:
            for remove in tagBlackListSource:
                if remove == tag:
                    to_remove.append(a)
                    break
            if "original work" == tag:
                to_remove.append(a)
        else:
            for remove in tagBlackListSource:
                if remove == tag:
                    remove_original = True
                    break

        if Prefs['hideUsefulMiscTags']:
            for remove in tagBlackListUsefulHelpers:
                if remove == tag:
                    to_remove.append(a)
                    break
            if tag.startswith("preview"):
                to_remove.append(a)

        if Prefs['hideSpoilerTags']:
            for remove in tagBlackListPlotSpoilers:
                if remove == tag:
                    to_remove.append(a)
                    break
            if tag.startswith("plot"):
                to_remove.append(a)
            if tag.endswith(" dies"):
                to_remove.append(a)
            if tag.endswith(" end"):
                to_remove.append(a)
            if tag.endswith(" ending"):
                to_remove.append(a)

        if Prefs['hideMiscTags']:
            for remove in tagBlacklistAniDBHelpers:
                if remove == tag:
                    to_remove.append(a)
                    break
            if "to be" in tag:
                if "merged" in tag:
                    to_remove.append(a)
                elif "deleted" in tag:
                    to_remove.append(a)
                elif "split" in tag:
                    to_remove.append(a)
                elif "moved" in tag:
                    to_remove.append(a)
                elif "improved" in tag or "improving" in tag or "improvement" in tag:
                    to_remove.append(a)
            elif "need" in tag or "needs" in tag:
                if "merging" in tag or "merged" in tag:
                    to_remove.append(a)
                elif "deleting" in tag or "deleted" in tag:
                    to_remove.append(a)
                elif "moving" in tag or "moved" in tag:
                    to_remove.append(a)
                elif "improved" in tag or "improving" in tag or "improvement" in tag:
                    to_remove.append(a)
            elif "old animetags" in tag:
                to_remove.append(a)
            elif "missing" in tag:
                to_remove.append(a)
            elif tag.startswith("predominantly"):
                to_remove.append(a)
            elif tag.startswith("weekly"):
                to_remove.append(a)

    toAdd = []
    # on a separate loop in case 'original work' came before the source
    if remove_original:
        for a in string:
            tag = str(a).lower().strip()
            if tag == "new":
                toAdd.append('Original Work')
            elif tag == "original work":
                to_remove.append("original work")
                # both just in case
                to_remove.append("Original Work")
                break

    for a in to_remove:
        if a in string:
            string.remove(a)

    for a in toAdd:
        if a not in string:
            string.append(a)

    return string
