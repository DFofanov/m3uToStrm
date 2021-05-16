#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import requests
import json

from bs4 import BeautifulSoup
import os
import http.cookiejar
import re
import urllib.parse
import urllib.request

import time
import datetime

# Подключаем библиотеку tmdb3
# from tmdb3 import set_key, set_locale, searchMovie
import tmdb3 as tmdb
# Подключаем библиотеку kinopoisk_api
from kinopoisk_api import KP

# Бибилиотеки для вызова утилиты ffprobe
from subprocess import PIPE
from subprocess import Popen
from subprocess import TimeoutExpired

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.46 Safari/537.36 OPR/60.0.3255.8 (Edition beta)'}  

PROBE_COMMAND = (
    'ffprobe -hide_banner -show_streams -select_streams v '
    '-of json=c=1 -v quiet'
)

directory = '/Users/fofanov.dmitry/Projects/'
m3u_file = 'ott.m3u8'
#m3u_file = 'megogo.m3u'
#m3u_file = '195_Kinokolekcia.m3u'

provider_prifix = 'ott'
path_name = 'Strm'

tmdb_key = '1e5af542a2069e37d4ce990ad61946e0'
kinopoisk_key = '6858ec1f-37af-4774-aafd-51775f042087'

timeout_value = 120

class track():
    def __init__(self, title, path, logo):
        self.title = title
        self.path = path
        self.logo = logo

def ParseM3U(infile):
    try:
        assert(type(infile) == '_io.TextIOWrapper')
    except AssertionError:
        infile = open(infile,'r')

    line = infile.readline()
    if not '#EXTM3U' in line:
        return

    # initialize playlist variables before reading file
    playlist=[]
    song = track(None,None,None)

    for line in infile:

        line = line.strip()
        if line.startswith('#EXTINF:'):
            # pull length and title from #EXTINF line
            if 'tvg-logo' in line:
                logo = re.findall(re.compile(r'tvg-logo="(.*)"'), line)[0]
            else: logo = None
            title = line[line.find(',')+1:]
            song = track(title,None,logo)
        elif (len(line) != 0) and ('http' in line):
            # pull song path from all other, non-blank lines
            song.path = line
            playlist.append(song)
            # reset the song variable so it doesn't use the same EXTINF more than once
            song = track(None,None,None)

    infile.close()

    return playlist

def CreateDir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def SaveStrm(folder, filename, text):
    CreateDir(folder)
    try:
        f = open(folder + filename,"w+")
        f.write(text)
    finally:
        f.close()

def Probe(url, timeout=None):
    """Invoke probe to get stream information."""
    outs = None
    proc = Popen(f'{PROBE_COMMAND} {url}'.split(), stdout=PIPE, stderr=PIPE)
    try:
        outs, dummy = proc.communicate(timeout=timeout)
    except TimeoutExpired:
        proc.kill()
    if outs:
        try:
            return json.loads(outs.decode('utf-8'))
        except json.JSONDecodeError as exc:
            print(exc)
    return None

# Узнаем качество видео с помощью утилиты ffprobe
def GetQuality(url,timeout_value):
    quality = None
    obj_probe = Probe(url,timeout_value)
    if obj_probe != None and len(obj_probe) > 0:
        if len(obj_probe["streams"]) > 0:
            width = obj_probe["streams"][0]["width"]
            quality = GetCategory(width)
    return quality

# Сохраняем постер в папке
def SavePoster(folder,filename,url):
    ext = os.path.splitext(url)[1]
    try:
        response = requests.get(url, verify=False)
        with open(folder + "/" + filename + ext, "wb") as file:
            file.write(response.content)
    except:
        pass

def GetCategory(width):
    category = None
    if (width <= 256): category = '144p'
    elif (width in range(426, 640)): category = '240p'
    elif (width in range(640, 854)): category = '360p'
    elif (width in range(854, 1280)): category = '480p'
    elif (width in range(1280, 1920)): category = '720p'
    elif (width in range(1920, 2560)): category = '1080p'
    elif (width in range(2560, 3840)): category = '1440p'
    elif (width >= 3840): category = '2160p'
    return category

torrent_pattern = re.compile(r'''<tr class=".*"><td>.*</td><td.*><a class="downgif" href="(?P<link>.+)"><img src=".+" alt="D" /></a><a href=".+"><img src=".+" alt="M" /></a>\s*<a href="(?P<desc_link>.+)">(?P<name>.+)?\s</a></td>\s*(<td align="right">.+<img.*></td>)?\s*<td align="right">(?P<size>.+)</td><td align="center"><span class="green"><img src=".+" alt="S" />.*(?P<seeds>\d+)</span> <img src=".*" alt="L" /><span class="red">.*(?P<leech>\d+)</span></td></tr>''')

tag = re.compile(r'<.*?>')

class rutor(object):
    
    ''' RUTOR.ORG Russian free tracker '''
    url = 'http://rutor.info'
    name = 'rutor.org'
    supported_categories = {'all': 0,
                            'movies': 1,
                            'tv': 6,
                            'music': 2,
                            'games': 8,
                            'anime': 10,
                            'software': 9,
                            'pictures': 3,
                            'books': 11}

    query_pattern = '%(url)s/search/%(start)i/%(f)i/100/2/%(q)s'
    cookie_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)),name + ".cookies")
    cookie_pattern = re.compile(r'''document.cookie.indexOf\('(?P<name>.+)=(?P<value>.+)'\)''')

    def __init__(self):
        pass

    def retrieve_url(self,url):
        cj = http.cookiejar.MozillaCookieJar(self.cookie_filename)
        if os.access(self.cookie_filename, os.F_OK):
            cj.load()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        req = urllib.request.Request(url)
        response = opener.open(req)
        dat = response.read()
 
        m = re.search(self.cookie_pattern, dat.decode('utf-8'))
        if m:
            ck = http.cookiejar.Cookie(version=0, name=m.group('name'), value=m.group('value'), port=None, port_specified=False, domain=self.name, domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
            cj.set_cookie(ck)
            cj.save(self.cookie_filename, ignore_discard=True, ignore_expires=True)
            response = opener.open(req)
            dat = response.read()

        return dat

    def search_page(self, what, cat, start):
        params = {'url': self.url,
                'q': urllib.parse.quote(what),
                'f': self.supported_categories[cat],
                'start': start}
        dat = self.retrieve_url(self.query_pattern % params).decode('utf-8')
        soup = BeautifulSoup(dat)
        file_url = soup.find("div",attrs = {"id":"index"}).findAll("a")[2]['href']

        dat = self.retrieve_url(self.url + file_url).decode('utf-8')
        soup = BeautifulSoup(dat)
        
        atr = soup.find("table",attrs = {"id":"details"})
        for info in atr.text.split('\n'):
            if info == 'название':
                print(info)
        
    def search(self, what, cat='all'):
        start = 0
        f = True
        while f:
            f = False
            for d in self.search_page(what, cat, start):
                if __name__ != "__main__":
                    prettyPrinter(d)
                f = True
            start += 1

def SaveNFO(filename,nfo_info):
    try:
        f = open(filename,"w+")
        f.write('<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n')
        f.write('<movie>\n')
        if nfo_info.get('plot') != None:
            f.write('  <plot><![CDATA[' + nfo_info.get('plot') + ']]></plot>\n')
        f.write('  <outline />\n')
        f.write('  <lockdata>false</lockdata>\n')
        f.write('  <dateadded>' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + '</dateadded>\n')
        f.write('  <title>' + nfo_info.get('title') + '</title>\n')
        f.write('  <originaltitle>' + nfo_info.get('originaltitle') + '</originaltitle>\n')
        if nfo_info.get('rating') != None:
            f.write('  <rating>' + str(nfo_info.get('rating')) + '</rating>\n')
        f.write('  <year>' + nfo_info.get('year') + '</year>\n')
        f.write('  <imdbid>' + nfo_info.get('imdbid') + '</imdbid>\n')
        f.write('  <tmdbid>' + nfo_info.get('tmdbid') + '</tmdbid>\n')
        f.write('  <releasedate>' + nfo_info.get('releasedate') + '</releasedate>\n')
        f.write('</movie>\n')
    finally:
        f.close()    

def m3uToFileEmby():
    #m3ufile = sys.argv[1]
    m3ufile = directory + m3u_file
    playlist = ParseM3U(m3ufile)
    i = 0
    count = len(playlist)
    for track in playlist:
        i = i + 1
  
        title_array = track.title.split(' (')
        title = title_array[0]
        year = title_array[len(title_array)-1][0:-1]

        # Подключаем API ключ для tmdb3
        tmdb.set_key(tmdb_key)
        tmdb.set_locale('ru', 'RU')
        title_year = title + ' (' + year + ')'
        res = tmdb.searchMovieWithYear(title_year)


        nfo_info = {}        
        if len(res) > 0:
            try:
                nfo_info['plot'] = res[0].overview
                nfo_info['title'] = res[0].title
                nfo_info['originaltitle'] = res[0].originaltitle
                nfo_info['rating'] = ''
                nfo_info['year'] = year
                nfo_info['imdbid'] = res[0].imdb
                nfo_info['tmdbid'] = str(res[0].id)
                nfo_info['releasedate'] = str(res[0].releasedate)
                if res[0].poster != None:
                    nfo_info['poster'] = res[0].poster.geturl()
                if res[0].backdrop != None:
                    nfo_info['fanart'] = res[0].backdrop.geturl()
                if len(res[0].genres) > 0:
                    nfo_info['genre'] = res[0].genres[0].name
                Countries = ''
                for countrie in res[0].countries:
                    if len(Countries) == 0:
                        Countries = countrie.code
                    else: Countries = Countries + ',' + countrie.code
                nfo_info['countries'] = Countries
            except:
                pass
        else:
            try:
                kinopoisk = KP(token=kinopoisk_key)
                res = kinopoisk.search(track.title)
                if len(res) > 0:
                    kp_id = res[0].kp_id

                    nfo_info['title'] = res[0].ru_name
                    nfo_info['originaltitle'] = res[0].name
                    nfo_info['year'] =  str(res[0].year)
                    nfo_info['imdbid'] = ''
                    nfo_info['tmdbid'] = ''
                    if len(res[0].genres) > 0:
                        nfo_info['genre'] = res[0].genres[0]

                    Countries = ''
                    for countrie in res[0].countries:
                        if len(Countries) == 0:
                            Countries = countrie
                        else: Countries = Countries + ',' + countrie
                    nfo_info['countries'] = Countries
                    
                    res = kinopoisk.get_film(kp_id)
                    if res != None:
                        nfo_info['plot'] = res.description
                        nfo_info['rating'] = res.imdb_rate
                        nfo_info['releasedate'] = str(res.premiere)
                        nfo_info['poster'] = res.poster
                else:
                    # Узнаем качество видео с помощью утилиты ffprobe
                    quality = GetQuality(track.path,timeout_value)
                    if quality != None:
                        SaveStrm(directory + path_name + "/NoName/" + str(year) + "/" + title_year + "/", title_year + '-' + quality + ' [' + provider_prifix + ']' + '.strm', track.path)
                    print('NoName - ' + track.title)
            except:
                pass

        if len(nfo_info) > 0:
            # Узнаем качество видео с помощью утилиты ffprobe
            quality = GetQuality(track.path,timeout_value)
            if quality != None:
                if ('RU' in nfo_info.get('countries')) or ('Россия' in nfo_info.get('countries')):
                    if int(year) < 1991:
                        category_path = 'Советские фильмы'
                    else: category_path = 'Российские фильмы'
                else: 
                    if ('SU' in nfo_info.get('countries')) or ('СССР' in nfo_info.get('countries')):
                        category_path = 'Советские фильмы'
                    else: category_path = 'Зарубежные фильмы'
                genre = nfo_info.get('genre')
                if genre == 'мультфильм':
                    category_path = 'Мультфильмы'
                if genre == 'документальный':
                    category_path = 'Документальные фильмы'
                        
                # Создаем папку и сохраняем файл 
                SaveStrm(directory + path_name + "/" + category_path + "/" + str(year) + "/" + title_year.replace('/','') + "/", title_year.replace('/','') + '-' + quality + ' [' + provider_prifix + ']' + '.strm', track.path)
                SaveNFO(directory + path_name + "/" + category_path + "/" + str(year) + "/" + title_year.replace('/','') + '/' + title_year.replace('/','') + '-' + quality + ' [' + provider_prifix + ']' + '.nfo', nfo_info)
                if nfo_info.get('poster') != None:
                    # Сохраняем постер
                    SavePoster(directory + path_name + "/" + category_path + "/" + str(year) + "/" + title_year.replace('/',''), 'poster', nfo_info.get('poster'))
                if nfo_info.get('fanart') != None:
                    # Сохраняем задник
                    SavePoster(directory + path_name + "/" + category_path + "/" + str(year) + "/" + title_year.replace('/',''), 'fanart', nfo_info.get('fanart'))  

                print(str(i) + ' in ' + str(count) + ', ' + category_path + ': ' + title_year)

def main():
    m3uToFileEmby()

if __name__ == '__main__':
    main()