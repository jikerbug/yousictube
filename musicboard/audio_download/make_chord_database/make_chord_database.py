# -*- coding:utf-8 -*-
import youtube_dl
import librosa
import glob
import os.path
import vamp
import json

JSON_PATH = '../data.json'


def get_double_chord_list_with_url(chord_list_with_timestamp,
                                   url):  # 한글 파일명은 librosa에서 로딩이 안되기 때문에 filename_id로 wav파일을 저장
    # 확장자 변경
    chord_list = []
    for i in chord_list_with_timestamp:
        chord_list.append(i['label'])

    double_chord_list_with_url = []

    for idx in range(len(chord_list) - 1):
        if chord_list[idx] != 'N' and chord_list[idx + 1] != 'N':
            double_chord = chord_list[idx] + '-' + chord_list[idx + 1]
            double_chord_list_with_url.append(double_chord)

    double_chord_list_with_url.append(double_chord_list_with_url[-1].split('-')[-1] + '-' + url)

    return double_chord_list_with_url


def playlist_to_audio_data(playlist_url, json_path):
    ydl = youtube_dl.YoutubeDL({
        'format': 'best',

    })

    with ydl:
        result = ydl.download([playlist_url])

    # 확장자 변경
    files = glob.glob("*.mp4")

    chord_list_dict = {}
    with open(json_path, 'r', encoding='utf-8') as f:
        chord_list_dict = json.load(f)

    for x in files:
        filename = os.path.splitext(x)
        id = filename[0].split('-')[-1]
        new_name_by_id = id + '.wav'  # librosa가 한글 파일을 읽을수 없어서 파일명 변경
        os.rename(x, new_name_by_id)
        signal, sr = librosa.load(new_name_by_id)  # (signal, sr) 형태로 저장
        os.remove(new_name_by_id)
        chord_list_with_timestamp = vamp.collect(signal, sr, "nnls-chroma:chordino")
        file_url = 'https://www.youtube.com/watch?v=' + id

        double_chord_list_with_url = get_double_chord_list_with_url(chord_list_with_timestamp['list'], file_url)

        # 아마 id만 제거하는 함수인듯...
        dict_key_music_name = ''
        for idx in range(len(filename[0].split('-')) - 1):
            dict_key_music_name += filename[0].split('-')[idx]

        chord_list_dict[dict_key_music_name] = double_chord_list_with_url

    with open(json_path, "w", encoding='utf-8') as fp:
        json.dump(chord_list_dict, fp, indent=4, ensure_ascii=False)


def multiple_playlist_to_audio_data(playlist_url_list, json_path):
    # data = {}
    # with open(json_path, "w", encoding='utf-8') as fp:
    #     json.dump(data, fp, indent=4)

    for playlist_url in playlist_url_list:
        playlist_to_audio_data(playlist_url, json_path)


if __name__ == "__main__":
    playlist_url_list = []
    playlist_url_list.append('https://www.youtube.com/playlist?list=PLUMJYOoO2JQ8UVF6Pv2x0UcN0T3i9qPBw') # 빌보드
    # playlist_url_list.append('https://www.youtube.com/playlist?list=PL2HEDIx6Li8jGsqCiXUq9fzCqpH99qqHV') # 멜론
    # playlist_url_list.append('https://www.youtube.com/playlist?list=OLAK5uy_mmEnAGjMCc_O7zheb5R7RHWvHM3Nh3ziY') # 아이유 팔레트
    # playlist_url_list.append('https://www.youtube.com/playlist?list=PL6Kcit5ZUQKjuFarGWB-S5Tr8eTHj01r9')
    # test = "https://www.youtube.com/playlist?list=PL6Kcit5ZUQKjuFarGWB-S5Tr8eTHj01r9"
    # playlist_url_list.append(test)

    json_path = JSON_PATH
    multiple_playlist_to_audio_data(playlist_url_list, json_path)








