#!/usr/bin/env python
#encoding: UTF-8

import hashlib
from neteaseApi import api

class MyNetease:
    def __init__(self):
        self.netease = api.NetEase()
        self.userId = (open("./userInfo", 'r').read())
        
    def songs_detail_new_api(self, music_ids):
        data = self.netease.songs_detail_new_api(music_ids)
        return data

    def get_recommend_playlist(self): # 每日推荐歌单
        music_list = self.netease.recommend_playlist()
        datalist = self.netease.dig_info(music_list, 'songs')
        playlist = []
        for data in datalist:
            music_info = {}
            music_info.setdefault("song_name", data.get("song_name"))
            music_info.setdefault("artist", data.get("artist"))
            music_info.setdefault("album_name", data.get("album_name"))
            music_info.setdefault("mp3_url", data.get("mp3_url"))
            music_info.setdefault("playTime", data.get("playTime"))  # 音乐时长
            music_info.setdefault("quality", data.get("quality"))
            playlist.append(music_info)
        return playlist

    def get_top_songlist(self):#热门单曲
        music_list = self.netease.top_songlist()
        datalist = self.netease.dig_info(music_list, 'songs')
        playlist = []
        for data in datalist:
            music_info = {}
            music_info.setdefault("song_id", data.get("song_id"))
            music_info.setdefault("song_name", data.get("song_name"))
            music_info.setdefault("artist", data.get("artist"))
            music_info.setdefault("album_name", data.get("album_name"))
            music_info.setdefault("mp3_url", data.get("mp3_url"))
            music_info.setdefault("playTime", data.get("playTime"))  # 音乐时长
            music_info.setdefault("quality", data.get("quality"))
            playlist.append(music_info)
        return playlist

    def login(self, username, password): #用户登陆
        password = hashlib.md5(password.encode('utf-8')).hexdigest()
        login_info = self.netease.login(username, password)
        if login_info['code'] == 200:
            res = u"登陆成功"
            #登陆成功保存userId，作为获取用户歌单的依据，userId是唯一的，只要登陆成功，就会保存在userInfo文件中，所以不必每次都登陆
            userId = login_info.get('profile').get('userId')

            self.userId = userId
            file = open("./userInfo", 'w')
            file.write(str(userId))
            file.close()
            file = open("./logInfo", 'w')
            file.write(str(login_info))
            file.close()
        else:
            res = u"登陆失败%s" % login_info
        return res

    def get_user_playlist(self):  #获取用户歌单
        playlist = self.netease.user_playlist(self.userId)  # 用户歌单
        # print(playlist)
        return playlist

    def get_song_list_by_playlist_id(self, playlist_id):
        songs = self.netease.playlist_detail(playlist_id)
        # print(songs)
        # for s in songs:
        #     print(s)
        song_list = self.netease.dig_info(songs, 'songs')
        return song_list

    def search_by_name(self, song_name):
        data = self.netease.search(song_name)
        song_ids = []
        if 'songs' in data['result']:
            if 'mp3Url' in data['result']['songs']:
                songs = data['result']['songs']

            else:
                for i in range(0, len(data['result']['songs'])):
                    song_ids.append(data['result']['songs'][i]['id'])
                songs = self.netease.songs_detail(song_ids)
        song_list = self.netease.dig_info(songs, 'songs')
        return song_list


if __name__ == '__main__':
    myNetease = MyNetease()
    myNetease.get_top_songlist()