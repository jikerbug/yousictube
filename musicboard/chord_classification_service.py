import operator
import librosa
# pip install librosa

import vamp

"""
1. pip install vamp
2. https://code.soundsoftware.ac.uk/projects/vamp-plugin-pack 에서 운영체제에 맞는 exe파일을 받고 Chordino and NNLS chroma 플러그인만 설치
"""

import glob
import os.path
import youtube_dl
import json

import numpy as np
import tensorflow.keras as keras #pip install tensorflow-cpu

from PIL import Image, ImageDraw, ImageFont # pip install pillow

SAMPLES_TO_CONSIDER = 22050 # 이것이 일초
MODEL_PATH = 'model_final_ver3.h5'
JSON_PATH = 'data.json'


class _Chord_Classification_Service:

    model = None
    _instance = None
    _mappings = []

    def predict(self, bothchroma_list):

        prediction_list =[]
        for i in bothchroma_list:


            chromagram = np.array(i["chromagram"])[np.newaxis, ...]

            # input_shape = (1, 20, 24) (number of slices extract Chromagram, Chromagram)
            preditioncs = self.model.predict(chromagram) #[  [0.1, 0.6, 0.1, ...]  ]
            predicted_index = np.argmax(preditioncs)
            predicted_keyword = self._mappings[predicted_index]
            temp_dict = {"timestamp": i["timestamp"], "label": predicted_keyword}
            prediction_list.append(temp_dict)
        return prediction_list


    def add_recommend_database(self, url, json_path, working_directory_path):

        SAVE_PATH = '/'.join(os.getcwd().split('/')[:3]) + '/' + working_directory_path
        ydl_opts = {
            'format': 'best',
            'outtmpl': SAVE_PATH + '/%(title)s.%(ext)s',
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 확장자 변경
        files = glob.glob(working_directory_path + "/*.mp4")
        audio_file_name = ''

        signal, sr = 0, 0
        for x in files:
            if not os.path.isdir(x):
                filename = os.path.splitext(x)
                audio_file_name = str(filename[0].split(working_directory_path + '\\')[1])
                signal, sr = librosa.load(x)
                os.remove(x)

        # load audio file
        predicted_chord_list = vamp.collect(signal, sr, "nnls-chroma:chordino")
        chord_list_with_timestamp = predicted_chord_list["list"]

        chord_list = []
        for i in chord_list_with_timestamp:
            chord_list.append(i['label'])

        double_chord_list_with_url = []

        for idx in range(len(chord_list) - 1):
            if chord_list[idx] != 'N' and chord_list[idx + 1] != 'N':
                double_chord = chord_list[idx] + '-' + chord_list[idx + 1]
                double_chord_list_with_url.append(double_chord)

        double_chord_list_with_url.append(double_chord_list_with_url[-1].split('-')[-1] + '-' + url)

        # dict_key_music_name = ''
        # for idx in range(len(audio_file_name.split('-')) - 1):
        #     dict_key_music_name += audio_file_name.split('-')[idx]
        dict_key_music_name = audio_file_name

        with open(json_path, 'r', encoding='utf-8') as f:
            chord_list_dict = json.load(f)


        if dict_key_music_name not in chord_list_dict:
            chord_list_dict[dict_key_music_name] = double_chord_list_with_url
            with open(json_path, "w", encoding='utf-8') as fp:
                json.dump(chord_list_dict, fp, indent=4, ensure_ascii=False)



    def LSTM_load_audio_data_from_url(self, url):

        # ----- 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 경우에 파일을 제거 ------ #
        files = glob.glob("*.mp4")
        for x in files:
            if not os.path.isdir(x):
                os.remove(x)
        # ----- 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 경우에 파일을 제거 ------ #

        # working directory : main folder
        ydl_opts = {
            'format': 'best',

        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob("*.mp4")
        audio_file_name = ''

        signal, sr = 0, 0
        for x in files:
            if not os.path.isdir(x):
                filename = os.path.splitext(x)
                audio_file_name = filename[0]
                signal, sr = librosa.load(x)
                os.remove(x)

        predicted_beat_list = vamp.collect(signal, sr, "beatroot-vamp:beatroot")
        predicted_chord_list = vamp.collect(signal, sr, "nnls-chroma:chordino")

        chord_list = []
        for i in predicted_chord_list['list']:

            if i['label'] != 'N':
                i['timestamp'] = float(i['timestamp'])
                chord_list.append(i)

        beat_list = []
        for i in predicted_beat_list['list']:
            beat_list.append(float(i['timestamp']))

        bothchroma_list = []
        for idx in range(len(chord_list) - 1):

            start = int(chord_list[idx]["timestamp"] * SAMPLES_TO_CONSIDER)
            end = int(chord_list[idx + 1]["timestamp"] * SAMPLES_TO_CONSIDER)

            # (20이상,24)을 (20,24)로 맞추는 작업
            interval_signal = 0
            interval_chroma_list = []

            if(end - start >= 40960):
                interval_signal = signal[start:start+40960]
                interval_chroma_list = vamp.collect(interval_signal, sr, "nnls-chroma:nnls-chroma", output="bothchroma")
                interval_chroma_list = list(interval_chroma_list['matrix'])[1].tolist()
            else:
                interval_signal = signal[start:end]
                interval_chroma_list = vamp.collect(interval_signal, sr, "nnls-chroma:nnls-chroma", output="bothchroma")
                interval_chroma_list = list(interval_chroma_list['matrix'])[1].tolist()
                if (len(interval_chroma_list) < 20):
                    while (len(interval_chroma_list) != 20):
                        interval_chroma_list.append(interval_chroma_list[-1])

            temp_dict = {"timestamp": chord_list[idx]["timestamp"], "chromagram": interval_chroma_list}

            bothchroma_list.append(temp_dict)

        # 마지막 코드(chord) 출력 위함

        start = int(chord_list[-1]["timestamp"] * SAMPLES_TO_CONSIDER)
        last_interval_signal = signal[start:]

        interval_chroma_list = vamp.collect(last_interval_signal, sr, "nnls-chroma:nnls-chroma", output="bothchroma")
        interval_chroma_list = list(interval_chroma_list['matrix'])[1].tolist()

        if (len(interval_chroma_list) > 20):
            interval_chroma_list = interval_chroma_list[:21]
            if (len(interval_chroma_list) == 21):
                interval_chroma_list.pop()  # 이상하게 21 나오는 경우가 있어서 끝값 삭제
        elif (len(interval_chroma_list) < 20):
            while (len(interval_chroma_list) != 20):
                interval_chroma_list.append(interval_chroma_list[-1])

        temp_dict = {"timestamp": chord_list[idx]["timestamp"], "chromagram": interval_chroma_list}
        bothchroma_list.append(temp_dict)

        LSTM_model_predicted_chord_list = self.predict(bothchroma_list)

        return LSTM_model_predicted_chord_list, beat_list


    # 유튜브 url로부터 시간별 코드리스트, 비트리스트, 유튜브 추출 파일 이름을 반환하는 함수
    def load_audio_data_from_url(self, url, working_directory_path):

        # ----- 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 경우에 파일을 제거 ------ #
        files = glob.glob(working_directory_path + "/*.mp4")
        for x in files:
            if not os.path.isdir(x):
                os.remove(x)
        # ----- 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 경우에 파일을 제거 ------ #

        SAVE_PATH = '/'.join(os.getcwd().split('/')[:3]) + '/' + working_directory_path
        ydl_opts = {
            'format': 'best',
            'outtmpl': SAVE_PATH + '/%(title)s.%(ext)s',
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 확장자 변경
        files = glob.glob(working_directory_path + "/*.mp4")
        audio_file_name = ''

        signal, sr = 0, 0
        for x in files:
            if not os.path.isdir(x):
                filename = os.path.splitext(x)
                audio_file_name = filename[0].split(working_directory_path + '\\')[1]
                signal, sr = librosa.load(x)
                os.remove(x)

        # load audio file

        predicted_beat_list = vamp.collect(signal, sr, "beatroot-vamp:beatroot")

        predicted_chord_list = vamp.collect(signal, sr, "nnls-chroma:chordino")

        chord_list = []
        for i in predicted_chord_list['list']:
            i['timestamp'] = float(i['timestamp'])
            chord_list.append(i)

        beat_list = []
        for i in predicted_beat_list['list']:
            beat_list.append(float(i['timestamp']))

        return chord_list, beat_list, audio_file_name.split('-')[0]

    # load_audio_data_from_url로부터 정보를 받아와 악보를 저장하는 함수
    def make_music_sheet(self, url, title, working_directory_path, isLSTM):

        chord_list = []
        beat_list = []
        if(isLSTM):
            chord_list, beat_list = self.LSTM_load_audio_data_from_url(url)
        else:
            chord_list, beat_list, audio_file_name = self.load_audio_data_from_url(url, working_directory_path)

        # print(chord_list)
        # print(beat_list)
        # print(len(beat_list))

        # for문을 돌다가 마지막 element에 도달하기 전에 끊기지 않게 하기 위함
        while ((len(beat_list) + 6) % 16 != 0):
            beat_list.append(beat_list[-1])
        # print(len(beat_list))
        beat_list.append(beat_list[-1])



        text = ''
        longest_line_length = len(title) # 추후에 악보 이미지 파일 width를 정해주기 위함

        text += title
        text += '\n\n\n'

        total_chord_cnt = 0
        beat_flag = 0

        add_line = ''
        for chord in chord_list:
            if chord['timestamp'] >= 0 and chord['timestamp'] < beat_list[0]:
                if chord['label'] == 'N':
                    continue
                add_line += chord['label'] + '  '
                total_chord_cnt += 1
        text += add_line
        if(len(add_line) > longest_line_length):
            longest_line_length = len(add_line)

        init_flag = True
        for beat_id in range(len(beat_list)):
            if init_flag == False:
                if beat_flag != 16:
                    beat_flag += 1
                    continue
            else:
                if beat_flag != 10:
                    beat_flag += 1
                    continue
                init_flag = False

            add_line = ''
            for chord in chord_list:
                if chord['timestamp'] >= beat_list[beat_id - beat_flag] and chord['timestamp'] < beat_list[beat_id]:
                    add_line += chord['label'] + '  '
                    total_chord_cnt += 1
            text += add_line
            if (len(add_line) > longest_line_length):
                longest_line_length = len(add_line)
            text += '\n\n'
            beat_flag = 0

        add_line = ''
        for chord in chord_list:
            if chord['timestamp'] >= 0 and chord['timestamp'] < beat_list[0]:
                if chord['label'] == 'N':
                    continue
                add_line += chord['label'] + '  '
                total_chord_cnt += 1
        text += add_line
        if (len(add_line) > longest_line_length):
            longest_line_length = len(add_line)

        sheet_height = len(text.split('\n\n'))
        sheet_width = longest_line_length * 35

        # 한글 제목이 너무 긴경우 이미지 파일 크기가 안맞기 때문에 다른 기준으로 조정
        sheet_width_alt = int(250 * total_chord_cnt / sheet_height)
        if sheet_height * 90 / sheet_width_alt > 6:
            sheet_width_alt += int(sheet_height * 90 / sheet_width_alt) * 23
        if(sheet_width_alt > sheet_width):
            sheet_width = sheet_width_alt
        # --------------------------------------------------------------


        font = ImageFont.truetype('C:/Windows/Fonts/batang.ttc', 45)
        img = Image.new(mode='RGB', size=(sheet_width, sheet_height * 90), color='#FFF')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), text, font=font, fill='#000')

        music_sheet_path = 'music_sheet_img/' + title

        if(not isLSTM):
            music_sheet_path += '_quick'

        music_sheet_path += '.png'

        img.save(music_sheet_path, format='PNG')

        return music_sheet_path

    def get_top_three_similar_chord_music(self, url, music_subject, json_path, working_directory_path):

        # 1. 연속코드 비교

        # 1. 중복없는, 코드 종류 리스트 저장 ***  이거로 기존의 chord_list를 대체
        # 2. 저장된 데이터에서 비교!
        chord_list_with_timestamp, beat_list, audio_file_name = self.load_audio_data_from_url(url, working_directory_path)
        # print(chord_list_with_timestamp)

        double_chord_list = self.get_double_chord_list(chord_list_with_timestamp)
        double_chord_name_list = list(set(double_chord_list))
        # print(double_chord_name_list)

        single_chord_list = []
        for chord in chord_list_with_timestamp:
            single_chord_list.append(chord['label'])
        single_chord_name_list = list(set(single_chord_list))
        # print(single_chord_name_list)

        same_double_chord_cnt_dict = {}
        same_double_chord_total_cnt_dict = {}

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for key, value in data.items():
            if key == audio_file_name:
                continue  # 자기자신과는 비교 ㄴㄴ
            total_cnt = 0
            same_chord_progression_cnt = {}
            for cont_chord_data in value:
                for cont_chord in double_chord_name_list:
                    if cont_chord_data == cont_chord:
                        if cont_chord not in same_chord_progression_cnt:
                            same_chord_progression_cnt[cont_chord] = 1
                        else:
                            same_chord_progression_cnt[cont_chord] += 1
                        total_cnt += 1

            music_url = value[-1].split('-')[-1]

            same_double_chord_total_cnt_dict[key + "-url:" + music_url] = total_cnt
            same_double_chord_cnt_dict[key + "-url:" + music_url] = same_chord_progression_cnt

        sorted_dict = sorted(same_double_chord_total_cnt_dict.items(), key=operator.itemgetter(1), reverse=True)
        top_three_double_chord_dict = sorted_dict[:3]

        top_three_double_chord_info_dict = {}
        for music in top_three_double_chord_dict:
            top_three_double_chord_info_dict[music[0].split('-url:')[0]] = {"total_count": music[1],
                                                                            "chord_count": same_double_chord_cnt_dict[
                                                                                music[0]],
                                                                            "url": music[0].split('-url:')[-1]}




        # 2. 단일코드 비교

        same_single_chord_cnt_dict = {}
        same_single_chord_total_cnt_dict = {}

        for key, value in data.items():
            if key == audio_file_name:
                continue  # 자기자신과는 비교 ㄴㄴ
            total_cnt = 0
            same_chord_cnt = {}
            for cont_chord_data in value:
                for single_chord in single_chord_name_list:
                    single_chord_data = cont_chord_data.split('-')[0]
                    if single_chord_data == single_chord:
                        if single_chord not in same_chord_cnt:
                            same_chord_cnt[single_chord] = 1
                        else:
                            same_chord_cnt[single_chord] += 1
                        total_cnt += 1

            # data.json의 마지막 더블 코드의 두번째 코드가 반영이 안되는 것을 보완! -> 마지막 데이터 저장형태를 chord-url로 바꿔서 생략
            # for single_chord in single_chord_name_list:
            #     if value[-1].split('-')[-1] == single_chord:
            #         if single_chord not in same_chord_progression_cnt:
            #             same_chord_progression_cnt[single_chord] = 1
            #         else:
            #             same_chord_progression_cnt[single_chord] += 1
            #         total_cnt += 1

            music_url = value[-1].split('-')[-1]

            same_single_chord_total_cnt_dict[key + "-url:" + music_url] = total_cnt
            same_single_chord_cnt_dict[key + "-url:" + music_url] = same_chord_cnt

        sorted_dict = sorted(same_single_chord_total_cnt_dict.items(), key=operator.itemgetter(1), reverse=True)

        top_three_single_chord_dict = sorted_dict[:3]

        top_three_single_chord_info_dict = {}
        for music in top_three_single_chord_dict:
            top_three_single_chord_info_dict[music[0].split('-url:')[0]] = {"total_count": music[1],
                                                          "chord_count": same_single_chord_cnt_dict[music[0]],
                                                          "url": music[0].split('-url:')[-1]}
            # print(type(music))
            # music = list(music).append(same_single_chord_cnt_dict[music[0]])
            # music.append(music_url)
            # print(f'total count of same single chord of {music[0]} is {music[1]}')
            # print(same_single_chord_cnt_dict[music[0]])
            # print(music)

        info_data = {'double_chord': top_three_double_chord_info_dict, 'single_chord': top_three_single_chord_info_dict}
        info_path = 'music_recommend_info/' + music_subject + '_recommend.json'
        with open(info_path, "w", encoding='utf-8') as fp:
            json.dump(info_data, fp, indent=4)

        return top_three_double_chord_info_dict, top_three_single_chord_info_dict

    def get_double_chord_list(self, chord_list_with_timestamp):  # 한글 파일명은 librosa에서 로딩이 안되기 때문에 filename_id로 wav파일을 저장
        # 확장자 변경
        chord_list = []
        for i in chord_list_with_timestamp:
            chord_list.append(i['label'])
        double_chord_list = []

        for idx in range(len(chord_list) - 1):
            if chord_list[idx] != 'N' and chord_list[idx + 1] != 'N':
                double_chord = chord_list[idx] + '-' + chord_list[idx + 1]
                double_chord_list.append(double_chord)

        return double_chord_list


def Chord_Classification_Service():
    # singleton 구조

    # ensure that we only have 1 instance of CCS
    if _Chord_Classification_Service._instance is None:
        _Chord_Classification_Service._instance = _Chord_Classification_Service()
        _Chord_Classification_Service.model = keras.models.load_model(MODEL_PATH)
        type1 = ''
        type2 = 'm'
        type3 = 'b'
        type4 = 'bm'
        type5 = '#'
        type6 = '#m'
        type7 = 'maj7'
        type8 = 'm7'
        type9 = 'bmaj7'
        type10 = 'bm7'
        type11 = '#maj7'
        type12 = '#m7'
        type13 = '7'
        type14 = 'b7'
        type15 = '#7'
        type_table = [type1, type2, type3, type4, type5, type6, type7, type8, type9, type10, type11, type12, type13,
                      type14, type15]

        root_chord_list = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

        for chord_num, root_chord in enumerate(root_chord_list):
            for type_num, type in enumerate(type_table):
                _Chord_Classification_Service._mappings.append(root_chord + type)

        # _Chord_Classification_Service._mappings.append("N")

    return _Chord_Classification_Service._instance

if "__name__" == "__main__" :

    ccs = Chord_Classification_Service()

    let_it_be_url = 'https://www.youtube.com/watch?v=QDYfEBY9NM4'
    The_visitor_url = 'https://www.youtube.com/watch?v=y5YmTj8KDWM'
    brown_url = 'https://www.youtube.com/watch?v=-5duYTCCtqI'
    how_you_like_that_url = 'https://www.youtube.com/watch?v=ioNng23DkIM'

    title = ''
    ccs.make_music_sheet(brown_url, title)

    #
    # json_path = JSON_PATH
    # ccs.get_top_three_similar_chord_music(The_visitor_url, json_path)
