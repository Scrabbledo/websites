# -*- coding: utf-8 -*-
"""Copyright (C) 2013 COLDWELL AG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import time
import json
import gevent
import requests
from ... import hoster, debugtools, useragent
 
@hoster.host
class this:
    model = hoster.HttpHoster
    name = 'youtube-mp3.org'
    favicon_url = 'http://www.youtube-mp3.org/favicon.ico'
    patterns = [hoster.Matcher('ytmp3org', '*.youtube.com', '!/watch', v='id').set_tag('direct')]
    max_chunks = 1

def t():
    return int(time.time() * 1000)
 
def pushitem(file):
    s = requests.session()
    s.headers["User-Agent"] = useragent.get(None, None) # "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.22 Safari/537.36"
    s.headers['Accept-Location'] = '*'
    r = s.get('http://www.youtube-mp3.org/')
    print "r1", r.request.headers
    print "resp", r.headers
    s.headers["Referer"] = 'http://www.youtube-mp3.org'
    resp = s.get("http://www.youtube-mp3.org/a/pushItem/\
?item=http%3A//www.youtube.com/watch%3Fv%3D{}&el=na&bf=false&r={}".format(file.pmatch.id, t()))
    print "r2", resp.request.headers
    print "resp2", resp.headers
    return s, resp
 
def iteminfo(file, s, resp, code):
    resp = s.get('http://www.youtube-mp3.org/a/itemInfo/', params=dict(video_id=code))
    try:
        resp.raise_for_status()
        return json.loads(resp.content.replace('info = ', '').strip().strip(';'))
    except:
        fallback(file)
        #if 'pushItemYTError()' in resp.text:
        #    file.no_download_link()
        #file.no_download_link()
        
def fallback(file):
    #debugtools.add_links("ytinmp3://www.youtube.com/watch?v=" + file.pmatch.id, auto_accept=True)
    #file.delete_after_greenlet()
    file.retry('video too long or copyright problems', 1800)
 
def on_check(file):
    resp = file.account.get('http://www.youtube.com/watch?v=' + file.pmatch.id)
    try:
        title = resp.soup.find('meta', property='og:title')['content']
    except TypeError:
        file.set_infos(name="youtube - " + file.pmatch.id)
    else:
        file.set_infos(name=title + '.mp3')

def on_download(chunk):
    file = chunk.file
    s, resp = pushitem(file)
    if not resp.status_code == 200:
        fallback(file)
    code = resp.content.strip()
    if not code or "LIMIT" in code:
        file.retry("Limit reached", 60)
    info = iteminfo(file, s, resp, code)
    tx = 0
    try:
        while info['status'] != 'serving':
            if tx < time.time():
                tx = time.time() + 60.0
                with hoster.transaction:
                    chunk.waiting = tx
            gevent.sleep(3)
            info = iteminfo(file, s, resp, code)
            if info['title'] and file.name == "youtube - " + file.pmatch.id:
                file.set_infos(name=info['title'])
    finally:
        with hoster.transaction:
            chunk.waiting = None
    return 'http://www.youtube-mp3.org/get?video_id={}&h={}'.format(code, info['h'])
 
def on_initialize_account(account):
    account.set_user_agent()