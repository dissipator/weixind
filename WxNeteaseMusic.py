#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Filename:     weixind.py
# Author:       Liang Cha<ckmx945@gmail.com>
# CreateDate:   2014-05-15

import os
import time
import threading
from time import sleep
import subprocess
from myapi import MyNetease
import omxplayer


class WxNeteaseMusic(object):
    def __init__(self):
        self.help_msg = \
            u",P,H: 帮助信息\n" \
            u",P,P: 开始播放\n" \
            u",P,L: 登陆网易云音乐\n" \
            u",P,M: 播放列表\n" \
            u",P,N: 下一曲\n"\
            u",P,U: 用户歌单\n"\
            u",P,R: 正在播放\n"\
            u",P,S: 歌曲搜索\n"\
            u",P,T: 热门单曲\n"\
            u",P,G: 推荐单曲\n"\
            u",P,E: 退出\n"
        self.con = threading.Condition()
        self.myNetease = MyNetease()
        self.playlist = self.myNetease.get_top_songlist()  #默认是热门歌单
        self.song_index = 0
        self.playing = None    
        self.player = None
        ps = threading.active_count()
        ps = ps +1
        self.pname = "t%d" % ps
        self.t  = threading.Thread(name=self.pname,target=self.play)
        self.search_url = None 
        print("player up!!!!!!!!!!!!!!!!!!!")

    def msg_handler(self, args):
        print 'the msg_handler %s is running,' % (threading.current_thread().name)
        res = u"player:\n"
        if len(args) == 0:
            res = self.help_msg
            return res
        else:
            arg_list = args[0].split(':')  # 参数以空格为分割符
            #print (arg_list)
            if len(arg_list) == 0:
                res = self.help_msg
            elif len(arg_list) == 1:  # 如果接收长度为1
                arg = arg_list[0]
                if arg in [u'H',u'h']:  # 帮助信息
                    res = self.help_msg
                elif arg in [u'P']:  # 帮助信息
                    res = u'开始播放'
                    self.t.start()
                elif arg in [u'n',u'N']:  # 下一曲
                    if len(self.playlist) > 0:
                        if self.con.acquire():
                            self.con.notifyAll()
                            self.con.release()
                        res = u'切换成功，正在播放: ' + self. playlist[0].get('song_name')
                    else:
                        res = u'当前播放列表为空'
                elif arg in [u'U',u'u']:  # 用户歌单
                    user_playlist = self.myNetease.get_user_playlist()
                    if user_playlist == -1:
                        res = u"用户播放列表为空"
                    else:
                        index = 0
                        for data in user_playlist:
                            res += str(index) + ". " + data['name'] + "\n"
                            index += 1
                        res += u"\n 回复 (U 序号) 切换歌单"
                elif arg in [u'M',u'm']: #当前歌单播放列表
                    if len(self.playlist) == 0:
                        res = u"当前播放列表为空，回复 (U) 选择播放列表"
                    i = 0
                    for song in self.playlist:
                        res += str(i) + ". " + song["song_name"] + "\n"
                        i += 1
                    res += u'\n回复 (N) 播放下一曲， 回复 (N 序号)播放对应歌曲'
                elif arg in [u'R',u'r']: #当前正在播放的歌曲信息
                    song_info = self.playlist[-1]
                    artist = song_info.get("artist")
                    song_name = song_info.get("song_name")
                    album_name = song_info.get("album_name")
                    res = u"歌曲：" + song_name + u"\n歌手：" + artist + u"\n专辑：" + album_name
                elif arg in [u"S",u's']: #单曲搜索
                    res = u"回复 (S 歌曲名) 进行搜索"
                elif arg in [u'T',u't']: #热门单曲
                    self.playlist = self.myNetease.get_top_songlist()
                    if len(self.playlist) == 0:
                        res = u"当前播放列表为空，请回复 (U) 选择播放列表"
                    i = 0
                    for song in self.playlist:
                        res += str(i) + ". " + song["song_name"] + "\n"
                        i += 1
                    res += u'\n回复 (N) 播放下一曲， 回复 (N 序号)播放对应歌曲'
                elif arg in [u'G',u'g']:#推荐歌单
                    self.playlist = self.myNetease.get_recommend_playlist()
                    if len(self.playlist) == 0:
                        res = u"当前播放列表为空，请回复 (U) 选择播放列表"
                    i = 0
                    for song in self.playlist:
                        res += str(i) + ". " + song["song_name"] + "\n"
                        i += 1
                    res += u'\n回复 (N) 播放下一曲， 回复 (N 序号)播放对应歌曲'
                elif arg in [u'E',u'']:#关闭音乐
                    self.playlist = []
                    self.player.stop()
                    if self.con.acquire():
                        self.con.notifyAll()
                        self.con.release()
                        res = u'播放已退出，回复 (U) 更新列表后可恢复播放'
                else:
                    try:
                        index = int(arg)
                        if index > len(self.playlist) - 1:
                            res = u"输入不正确"
                        else:
                            if self.con.acquire():
                                self.con.notifyAll()
                                self.con.release()
                    except:
                        res = u'输入不正确'
            elif len(arg_list) == 2:  #接收信息长度为2
		#print 'arg_list: ' + arg_list[0]
                arg1 = arg_list[0]
                arg2 = arg_list[1]
                if arg1 in [u'U',u'u']:
                    user_playlist = self.myNetease.get_user_playlist()
                    if user_playlist == -1:
                        res = u"用户播放列表为空"
                    else:
                        try:
                            index = int(arg2)
                            data = user_playlist[index]
                            playlist_id = data['id']   #歌单序号
                            song_list = self.myNetease.get_song_list_by_playlist_id(playlist_id)
                            self.playlist = song_list
                            res = u"用户歌单切换成功，回复 (M) 可查看当前播放列表"
                            if self.con.acquire():
                                self.con.notifyAll()
                                self.con.release()
                        except:
                            res = u"输入有误"
                elif arg1 in [u'n',u'N']: #播放第X首歌曲
                    index = int(arg2)
                    tmp_song = self.playlist[index]
                    self.playlist.insert(0, tmp_song)
                    if self.con.acquire():
                        self.con.notifyAll()
                        self.con.release()
                    res = u'切换成功，正在播放: ' + self.playlist[0].get('song_name')
                    time.sleep(.5)
                    del self.playlist[-1]

                elif arg1 in [u's',u'S']: #歌曲搜索+歌曲名
                    song_name = arg2
                    song_list = self.myNetease.search_by_name(song_name)
                    res = ""
                    i = 0
                    for song in song_list:
                        res += str(i) + ". " + song["song_name"] + "\n"
                        i += 1
                    res += u"\n回复（S:歌曲名:序号）播放对应歌曲"
                    res += u"\n回复（D:歌曲名:序号）获取下载地址"
                elif arg1 in [u"cmd", u"CMD"]:
                    try:
                        res = str(os.popen(arg2).read())
                    except :
                        pass

            elif len(arg_list) == 3:   #接收长度为3
                arg1 = arg_list[0]
                arg2 = arg_list[1]
                arg3 = arg_list[2]
                try:
                    if arg1 == u'L':  #用户登陆
                        res = self.myNetease.login(arg2, arg3)
                    elif arg1 in [u's',u'S']:
                        song_name = arg2
                        song_list = self.myNetease.search_by_name(song_name)
                        index = int(arg3)
                        song = song_list[index]
                        #把song放在播放列表的第一位置，唤醒播放线程，立即播放
                        self.playlist.insert(0, song)
                        if self.con.acquire():
                            self.con.notifyAll()
                            self.con.release()
                        artist = song.get("artist")
                        song_name = song.get("song_name")
                        album_name = song.get("album_name")
                        res = u"歌曲：" + song_name + u"\n歌手：" + artist + u"\n专辑：" + album_name
                    elif arg1 in [u'd',u'D',]:
			song_name = arg2
			song_list = self.myNetease.search_by_name(song_name)
			index = int(arg3)
			song = song_list[index]
                        song_id = song['song_id']
                        artist = song.get("artist")
                        song_name = song.get("song_name")
                        album_name = song.get("album_name")
			res += u"歌曲：" + song_name + u"\n歌手：" + artist + u"\n专辑：" + album_name 
                        key = str(song_id)
			print(self.search_url)
                        if self.search_url != None and key in self.search_url.keys():
                            url = self.search_url.get(key)
                            res += u"\n url：%s" % url
                            return res
                        else:
                            res += u"\n请过0.5分钟后再试" 
                            get_t  = threading.Thread(name='get_t',target=self.get_newurl,args=(key,))
                            get_t.setDaemon(True)
                            get_t.start()                                
                            return res

                    elif arg1 in [u"CMD",u"cmd"]:
                        cmd = ''
                        for i in range(1,len(arg_list)):
                            if i>0 :
                                cmd += arg_list[i]+" "
                        print("cmd : " + cmd)
                        res = str(os.popen(cmd).read())
                        # self.send_msg(res)
                except Exception as e:
                    print e    
                    res = u"输入不正确"
        return res

    def get_newurl(self,song_id):
        #print("song_id",song_id)
        self.search_url = {song_id : self.myNetease.songs_detail_new_api([song_id])[0]['url']}
           
    def find_newurl(self,index):
        # print("find_newurl")
        index = int(index)
        if len(self.playlist)>index:
            song = self.playlist[index]
            # print("find url for %s " % song['song_id'] )
            song_data = self.myNetease.songs_detail_new_api([song['song_id']])
            if(song_data[0]['code'] == 200):
                self.playlist[index]["new_url"] = song_data[0]['url']
            # print('find_newurl done')
        print self.playlist[index]['song_id'],self.playlist[index]['song_name']

    def load_url(self):
        song = self.playlist[0]
        # print song
        if ('new_url' in song.keys()):
            new_url = song["new_url"] 
        else:
            self.find_newurl(0)
            new_url =  self.playlist[0]['new_url']
        # os.popen('sudo pkill omxplayer')
        try:
            self.player.stop()
        except:
            pass
        self.player = omxplayer.OMXPlayer(new_url, '-o local', start_playback=True, do_dict=True)
        next_t  = threading.Thread(name='next_t',target=self.find_newurl,args=('1',))
        # next_t.join()
        next_t.start()
        print("add url : %s ,%s " % (self.playlist[0]['song_id'],self.playlist[0]['song_name']))
        # print(": %s " % new_url)
        print 'the load_url threading  %s is ended' % threading.current_thread().name

    def play(self,song_time=0):
        name = self.pname
        print 'the play threading  %s is running,' % (threading.current_thread().name)
        while True:
            if self.con.acquire():
                pl = len(self.playlist) 
                print("name :play %s , playlist: %s" % (name,pl))
                # self.con.wait(5) #wait方法释放内部所占用的琐，同时线程被挂起，
                if len(self.playlist) != 0:
                    try:
                        self.load_url()
                    except:
                        pass
                    song = self.playlist[0]
                    next_song = self.playlist[1]
                    song_time = int(song.get('playTime'))/1000 
                    next_song_name = next_song["song_name"]
                    msg = "Next song is : %s " % ( next_song_name )
                    self.playlist.remove(song)
                    self.playlist.append(song)
                    self.con.notifyAll()
                    self.con.wait(song_time)
                else:
                    try:
                        self.con.notifyAll()
                        self.con.wait()
                    except:
                        pass
        print 'the curent threading  %s is ended' % threading.current_thread().name
