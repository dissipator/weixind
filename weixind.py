#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:     weixind.py
# Author:       Liang Cha<ckmx945@gmail.com>
# CreateDate:   2014-05-15

import web
import types
import hashlib
import base64
import memcache
from config import movie_location,omxoptions
import os, sys,  omxplayer, config, time, urllib
try:
    import RPi.GPIO as GPIO
except:
    pass
from lxml import etree
from weixin import WeiXinClient
from weixin import APIError
from weixin import AccessTokenError

import re
import threading
from time import sleep
import subprocess
from myapi import MyNetease


_TOKEN = ''
_URLS = (
    '/pc', 'pc',
    '/pc/files.ajax', 'files_ajax',
    '/files.ajax', 'files_ajax',
    '/info', 'info',
    '/player.ajax', 'webplayer',
    '/', 'index',
    '/weixin', 'weixinserver',
)
fromUser = 'o-'
toUser = ''
from WxNeteaseMusic import WxNeteaseMusic

playing = None
player = None
wnm = WxNeteaseMusic()

def check_input (videodir,track):
    if  os.path.exists(track):
       return True, track
    if '.' in track:
        path = videodir + track    
        if os.path.exists(path):
            return True, path
        else:
            print ("File " + path + " not found")
            return False ,None
    else:
        print track, " not understood"
        return False, None

def exec_command(command,file): 
    global player,playing
    if command == 'pause':    
    	player.toggle_pause()
    
    elif command == 'play':    
        if player != None and player.is_running():    
            exec_command('quit',file)
    
        ml = urllib.unquote(movie_location)    
        fil = urllib.unquote(file)
        checked,files = check_input(ml,fil)
        print (checked,files) 
        if checked == False:    
            return None
        player = omxplayer.OMXPlayer(files, omxoptions,start_playback=True, do_dict=True)
        playing = files
        print ('Playing: '+ str(files))

    elif command == 'ahead':    
        player.skip_ahead()
    
    elif command == 'back':    
        player.skip_back()
    
    elif command == 'quit':    
        player.stop()    
        playing = None    
        player = None

def _check_hash(data):
    signature = data.signature
    timestamp = data.timestamp
    nonce = data.nonce
    list = [_TOKEN, timestamp, nonce]
    list.sort()
    sha1 = hashlib.sha1()
    map(sha1.update, list)
    hashcode = sha1.hexdigest()
    if hashcode == signature: return True
    return False

def _check_user(user_id):
    print(user_id)
    user_list = ['o-mulxC3UJSgObM6eWM2S4JEOuVk']
    if user_id in user_list:
        return True
    return False

def _punctuation_clear(ostr):
    '''Clear XML or dict using special punctuation'''
    return str(ostr).translate(None, '\'\"<>&')

def _cpu_and_gpu_temp():
    '''Get from pi'''
    import commands
    try:
        fd = open('/sys/class/thermal/thermal_zone0/temp')
        ctemp = fd.read()
        fd.close()
        gtemp = commands.getoutput('/opt/vc/bin/vcgencmd measure_temp').replace('temp=', '').replace('\'C', '')
    except Exception as e:
        return (0, 0)
    return (float(ctemp) / 1000, float(gtemp))


def _json_to_ditc(ostr):
    import json
    try:
        return json.loads(ostr)
    except Exception as e:
        return None

def _get_user_info(wc):
    info_list = []
    wkey = 'wacthers_%s' % wc.app_id
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)
    id_list = mc.get(wkey)
    if id_list is None:
        return info_list
    for open_id in id_list:
        req = wc.user.info.dget(openid=open_id, lang='zh_CN')
        name ='%s' %(req.nickname)
        place = '%s,%s,%s' %(req.country, req.province, req.city)
        sex = '%s' %(u'男') if (req.sex == 1) else u'女'
        info_list.append({'name':name, 'place':place, 'sex':sex})
    return info_list

def _udp_client(addr, data):
    import select
    import socket
    mm = '{"errno":1, "msg":"d2FpdCByZXNwb25zZSB0aW1lb3V0"}'
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.setblocking(False)
    inputs = [c]
    c.connect(addr)
    c.sendall(data)
    readable, writeable, exceptional = select.select(inputs, [], [], 3)
    try:
        if readable: mm = c.recv(2000)
    except Exception as e:
        mm = '{"errno":1, "msg":"%s"}' %(base64.b64encode(_punctuation_clear(e)))
    finally:
        c.close()
    return mm

def _do_text_command(server, fromUser, toUser, content):
    print('_do_text_command')
    temp = content.split(',')
    try:
        return _weixin_text_command_table[temp[0]](server, fromUser, toUser, temp[1:])
    except KeyError as e:
        return server._reply_text(fromUser, toUser, u'Unknow command: '+temp[0])

def _do_text_command_security(server, fromUser, toUser, para):
    try:
        data = '{"name":"digitalWrite","para":{"pin":5,"value":%d}}' %(int(para[0]))
    except Exception as e:
        return server._reply_text(fromUser, toUser, str(e))
    buf = _udp_client(('10.0.0.100', 6666), data)
    data = _json_to_ditc(buf)
    errno = None
    reply_msg = None
    if type(data) is types.StringType:
        return server._reply_text(fromUser, toUser, data)
    errno = data['errno']
    if errno == 0:
        reply_msg = data['msg']
    else:
        reply_msg = buf
    return server._reply_text(fromUser, toUser, reply_msg)

def _do_text_command_pc(server, fromUser, toUser, para):
    if not _check_user(fromUser):
        return server._reply_text(fromUser, toUser, u'Permission denied…')
    if para[0] == 'wol':
        return _do_click_V3001_WAKEUP(server, fromUser, toUser, para)
    print (para[0])
    buf = _udp_client(('10.0.0.100', 55555), para[0])
    data = _json_to_ditc(buf)
    if not data:
        reply_msg = _punctuation_clear(buf.decode('gbk'))
    else:
        errno = data['errno']
        reply_msg = data['msg']
        reply_msg = (base64.b64decode(reply_msg)).decode('gbk') if reply_msg \
                else ('运行失败' if errno else '运行成功')
    return server._reply_text(fromUser, toUser, reply_msg)

def _do_text_command_kick_out(server, fromUser, toUser, para):
    msg = 'List is None.'
    wkey = 'wacthers_%s' % server.client.app_id
    try:
        mc = memcache.Client(['127.0.0.1:11211'], debug=0)
        wlist = mc.get(wkey)
        if wlist != None:
            del wlist[int(para[0])]
            mc.replace(wkey, wlist)
            msg = 'Kick out user index=%s' %para
    except Exception as e:
        msg = '_do_text_kick_out error, %r' % e
    return server._reply_text(fromUser, toUser, msg)

def _do_text_command_help(server, fromUser, toUser, para):
    data = "commands:\n"
    for (k, v) in _weixin_text_command_table.items():
        data += "\t%s\n" %(k)
    return server._reply_text(fromUser, toUser, data)

def _do_text_command_ss(server, fromUser, toUser, para):
    import ssc
    msg = ''
    def _unkonw_def():
        return 'unkonw ss command: %s' %para[0]
    ssdef = getattr(ssc, para[0], _unkonw_def)
    msg = ssdef(*para[1:])
    return server._reply_text(fromUser, toUser, msg)

def _do_text_command_TEMPERATURE(server, fromUser, toUser, doc):
    import dht11
    c, g = _cpu_and_gpu_temp()
    h, t = dht11.read(0)
    reply_msg = u'CPU : %.02f℃\nGPU : %.02f℃\n湿度 : %02.02f\n温度 : %02.02f' %(c, g, h, t)
    return server._reply_text(fromUser, toUser, reply_msg)

def _do_player(server, fromUser, toUser, msg, wnm=wnm):
    try:
        reply_msg = wnm.msg_handler(msg)
        return server._reply_text(fromUser, toUser, reply_msg)
    except :
        reply_msg = u"错误/稍后重试"
        return server._reply_text(fromUser, toUser, reply_msg)

def _do_voice(server, fromUser, toUser, msg, wnm=wnm):
    if msg in [u'下一首。']:
        return _do_player(server,fromUser, toUser, 'n', wnm=wnm)
    elif msg in [u'播放。',u'放歌。']:
        return _do_player(server,fromUser, toUser, 'P', wnm=wnm)

_weixin_text_command_table = {
    'help'                  :   _do_text_command_help,
    'kick'                  :   _do_text_command_kick_out,
    'pc'                    :   _do_text_command_pc,
    'ss'                    :   _do_text_command_ss,
    'tt'                    :   _do_text_command_TEMPERATURE,
    # 'status'                :   _do_status,
    'P'                     :   _do_player,
    'p'                     :   _do_player,
}

class weixinserver:

    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)
        self.client = WeiXinClient('', '')
        try:
            self.client.request_access_token()
        except Exception as e:
            self.client.set_access_token('ThisIsAFakeToken', 1800, persistence=True)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        #define GPIO pin
        pin_btn = 17
        pin_rd = 4
        pin_gr = 12
        pin_yl = 23

        # LED = {4:'pin_rd',12:'pin_gr',23:'pin_yl'}
        # print LED
        #GPIO.setup(pin_rd,GPIO.OUT,initial=GPIO.LOW)
        # GPIO.setup(pin_rd,GPIO.IN)
        # GPIO.setup(pin_rd,GPIO.OUT)
        # GPIO.setup(pin_yl,GPIO.IN)
        # GPIO.setup(pin_yl,GPIO.OUT)
        # GPIO.setup(pin_gr,GPIO.IN)
        # GPIO.setup(pin_gr,GPIO.OUT)

    def _recv_text(self, fromUser, toUser, doc):
        content = doc.find('Content').text
        # print(content)
        if content[0] == ',':
            return _do_text_command(self, fromUser, toUser, content[1:])
        reply_msg = content
        return self._reply_text(fromUser, toUser, reply_msg)

    def _recv_event(self, fromUser, toUser, doc):
        event = doc.find('Event').text
        try:
            return _weixin_event_table[event](self, fromUser, toUser, doc)
        except KeyError as e:
            return self._reply_text(fromUser, toUser, u'Unknow event:%s' %event)

    def _recv_image(self, fromUser, toUser, doc):
        url = doc.find('PicUrl').text
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/downloads/wx/wx_%s.jpg' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        return self._reply_text(fromUser, toUser, u'upload to:%s' %url)

    def _recv_voice(self, fromUser, toUser, doc):
        # import subprocess
        cmd = doc.find('Recognition').text
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/downloads/wx/wx_%s.amr' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        # subprocess.call(['omxplayer', '-o', 'local', fname])
        # cmds = "mplayer %s &" % fname
        # subprocess.Popen(cmds, shell=True)
        if cmd is None:
            return self._reply_text(fromUser, toUser, u'no Recognition, no command');
        print (cmd)
        try:
            msg = _do_voice(self, fromUser, toUser, cmd)
            self._reply_text(fromUser, toUser,int(time.time()), msg);
        except Exception as e:
            return self._reply_text(fromUser, toUser, u'Unknow recognition:%s' %cmd);

    def _recv_video(self, fromUser, toUser, doc):
        print('recv video')
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/downloads/wx/wx_%s.mp4' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        exec_command('play',fname)
        return self._reply_text(fromUser, toUser, u'video:%s' %fname);

    def _recv_shortvideo(self, fromUser, toUser, doc):
        print('recv sortvideo')
        mid = doc.find('MediaId').text
        rm = self.client.media.get.file(media_id=mid)
        fname = '/home/pi/downloads/wx/wx_%s.mp4' %(time.strftime("%Y_%m_%dT%H_%M_%S", time.localtime()))
        fd = open(fname, 'wb'); fd.write(rm.read()); fd.close(); rm.close()
        exec_command('play',fname)
        return self._reply_text(fromUser, toUser, u'shortvideo:%s' %fname);

    def _recv_location(self, fromUser, toUser, doc):
        pass

    def _recv_link(self, fromUser, toUser, doc):
        pass

    def _reply_text(self, toUser, fromUser, msg):
        return self.render.reply_text(toUser, fromUser, int(time.time()), msg)

    def _reply_image(self, toUser, fromUser, media_id):
        return self.render.reply_image(toUser, fromUser, int(time.time()), media_id)

    def _reply_news(self, toUser, fromUser, title, descrip, picUrl, hqUrl):
        return self.render.reply_news(toUser, fromUser, int(time.time()), title, descrip, picUrl, hqUrl)

    def GET(self):
        data = web.input()
        try:
            if _check_hash(data):
                return data.echostr
        except Exception as e:
            #print e
            return None

    def POST(self):
        str_xml = web.data()
        doc = etree.fromstring(str_xml)
        msgType = doc.find('MsgType').text
        fromUser = doc.find('FromUserName').text
        toUser = doc.find('ToUserName').text
        # print ('from:%s-->to:%s' %(fromUser, toUser))
        # print (msgType)
        if msgType == 'text':
            return self._recv_text(fromUser, toUser, doc)
        if msgType == 'event':
            return self._recv_event(fromUser, toUser, doc)
        if msgType == 'image':
            return self._recv_image(fromUser, toUser, doc)
        if msgType == 'voice':
            return self._recv_voice(fromUser, toUser, doc)
        if msgType == 'video':
            return self._recv_video(fromUser, toUser, doc)
        if msgType == 'shortvideo':
            return self._recv_shortvideo(fromUser, toUser, doc)
        if msgType == 'location':
            return self._recv_location(fromUser, toUser, doc)
        if msgType == 'link':
            return self._recv_link(fromUser, toUser, doc)
        else:
            return self._reply_text(fromUser, toUser, u'Unknow msg:' + msgType)

class files_ajax:
    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)
    
    def GET(self):
        dr = web.input(dr = None)
        if len(dr)>=1:
            dr = dr['dr']
        try:
            def comparator(x,y):
                if x[0].upper() > y[0].upper():
                    return 1
                if x[0].upper() < y[0].upper():
                    return -1
                return 0
            
            if dr == None:
                dr = ''
            else:
                dr = urllib.unquote(dr)
        
            d = []
            f = []
            for i in os.listdir(urllib.unquote(movie_location+'/'+dr)):
                if os.path.isdir(urllib.unquote(movie_location+'/'+dr+"/"+i)):
                    d.append([urllib.quote(i),i])
                else:
                    f.append([urllib.quote(i),i])
            f.sort(comparator)
            d.sort(comparator)
            return self.render.files_ajax( dir_list=d,file_list=f,dr=urllib.quote(dr))
        except:
            return "<div class='folders'><div class='error'>Error accessing that folder: " + str(sys.exc_info()[1]) + "</div></div>"

    def POST(self):
        return "Hello, world!"

class info:
    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
    def GET(self):
        file = web.input(file = None)['file']
        if file == None:
           return '00:00:00'

        ml = urllib.unquote(movie_location)
        fil = urllib.unquote(request.query.file)
        return omxplayer.file_info(ml+'/'+fil)

class webplayer:
    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)

    def GET(self):
        global playing
        c = web.input(c = None)['c']
        file = web.input(file = None)['file']
        if c != None and file != None:
            exec_command(c,file)

        if player:
            print(player.position,player.duration)
            return self.render.player_ajax(current=playing, pos=time.strftime('%H:%M:%S', time.gmtime(player.position)),length=player.duration)
        else:
            return self.render.player_ajax(current=playing, pos='00:00:00',length='00:00:00')

class index:
    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)

    def GET(self):
        return self.render.index( dir_list=[],file_list=[],dr='',current=playing)

class pc:
    def __init__(self):
        self.app_root = os.path.dirname(__file__)
        self.templates_root = os.path.join(self.app_root, 'templates')
        self.render = web.template.render(self.templates_root)
        print("threading total:",threading.active_count())

    def _reply_text(self, toUser, fromUser, msg):
        #print(toUser, fromUser, msg)
        return self.render.reply_text(toUser, fromUser, int(time.time()), msg)
    def _reply_dit(self, toUser, fromUser, msg):
        #print(toUser, fromUser, msg)
        return self.render.index(toUser, fromUser, int(time.time()), msg) 
    def GET(self):
        # name = 'Bob'
        i = web.input(cmd = None)
        content = i['cmd']
        #print(content[0])
        try:
            if content[0] == ',':
                return _do_text_command(self, 'fromUser', 'toUser', content[1:])
        except:
            return self.render.index( i.cmd)

    def POST(self):
        return "Hello, world!"


#application = web.application(_URLS, globals()).wsgifunc()
application = web.application(_URLS, globals())

if __name__ == "__main__":
    application.run()
