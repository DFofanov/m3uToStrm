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

# Подключаем библиотеку tmdb3
# from tmdb3 import set_key, set_locale, searchMovie
import tmdb3 as tmdb
#import tmdbsimple as tmdb

# Библиотека Kinopoisk.ru (https://github.com/ramusus/kinopoiskpy)
#from kinopoisk.movie import Movie

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
#m3u_file = '195_Kinokolekcia.m3u'

provider_prifix = 'hdru'
path_name = 'StrmEmby'

#timeout_value = 120

class track():
    def __init__(self, title, path, logo):
        self.title = title
        self.path = path
        self.logo = logo

def parsem3u(infile):
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

def create_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

def save_file(dir, filename, text):
    create_dir(dir)
    try:
        f = open(dir + filename,"w+")
        f.write(text)
    finally:
        f.close()

def probe(url, timeout=None):
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

def get_category(width):
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

        
#        print(atr[4].previous)
#        print(atr[6].previous)
#        print(atr[12].previous)
#        print(atr[13].next)

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

def m3uToFileEmby():
    #m3ufile = sys.argv[1]
    m3ufile = directory + m3u_file
    playlist = parsem3u(m3ufile)
    for track in playlist:
        title_array = track.title.split(' (')
        title = title_array[0]
        year = title_array[len(title_array)-1][0:-1]

        # Подключаем API ключ для tmdb3
        tmdb.set_key('1e5af542a2069e37d4ce990ad61946e0')
        tmdb.set_locale('ru', 'RU')
        title_year = title + ' (' + year + ')'
        res = tmdb.searchMovieWithYear(title_year)
        if len(res) > 0:
            try:
                for count in res[0].countries:
                    if ('RU' in count.code) and (int(year) < 1991):
                        if res[0].title != None:
                            print( res[0].title )
                        for count in res[0].countries:
                            print( count.code )
                        #print( res[0].countries[0].code )
                        print( res[0].originaltitle )
                        print( res[0].imdb )                
                        print( res[0].poster.geturl() )
                        print( res[0].backdrop.geturl() )                
            except:
                pass
        else:
            print(track.title)

        #print(track.title, track.path, track.logo)

"""
                print(res._request.full_url)
                #engine = rutor()
                #engine.search(rec_name)
                # http://rutor.info/search/0/0/100/0/%D0%92%D0%B5%D0%BD%D0%BE%D0%BC%20(2018)
                movies = Movie.objects.search(rec_name)
                if len(movies) > 0:
                    m = movies[0]
                    movie_name = m.title
                    movie_id = m.id
                    movie_year = m.year
                    movie_votes = m.votes
                    movie_imdb_votes = m.imdb_votes
                    m.get_content('posters')
                    if (len(m.posters) >0 ):
                        p = m.posters[0]
                year = rec['name'].split('(')[1][:4]
                quality = None
                # Узнаем качество видео с помощью утилиты ffprobe
                obj_probe = probe(rec['url'],timeout_value)
                if obj_probe != None and len(obj_probe) > 0:
                    if len(obj_probe["streams"]) > 0:
                        width = obj_probe["streams"][0]["width"]
                        quality = get_category(width)
                if quality != None:
                    # Создаем папку и сохраняем файл 
                    save_file(directory + "/" + path_name + "/" + str(year) + "/" + rec['name'] + "/", rec['name'] + '-' + quality + ' [' + provider_prifix + ']' + '.strm', rec['url'])
                    # Сохраняем logo
                    if rec['logo'] != None:
                        ext = os.path.splitext(rec['logo'])[1]
                        try:
                            response = requests.get(rec['logo'], verify=False)
                            with open(directory + "/" + path_name + "/" + str(year) + "/" + rec['name'] + "/poster" + ext, "wb") as file:
                                file.write(response.content)
                        except:
                            pass
            except:
                pass
            print('rec: ' + str(i))
 """
def main():
    m3uToFileEmby()

if __name__ == '__main__':
    main()