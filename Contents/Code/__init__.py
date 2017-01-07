import os, re, time, string, thread, threading, urllib, copy
from lxml import etree

def Start():
    Log("Shoko metata agent started")

class ShokoTVAgent(Agent.TV_Shows):
    name = 'My Agent' 
    languages = [ Locale.Language.English, ] 
    primary_provider = True 
    fallback_agent = False 
    accepts_from = None 
    contributes_to = None

    def search(self, results, media, lang, manual):

    def update(self, metadata, media, lang, force):

