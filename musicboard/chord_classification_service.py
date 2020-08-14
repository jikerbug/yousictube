"""

'/******************************************************************************
' 파일명    : chord_classification_service.py
' 작성자    : 임지백
' 목적      : 1. url을 입력받아 유튜브 음원으로부터 정보를 추출하고 코드를 예측(1. 텐서플로우 모델 / 2. vamp 플러그인)하여 악보를 파일을 저장
             2. 특정 음원의 코드를 기준으로 json 파일에 저장된 유사 코드 음악을 추천
' 사용방식  : chord_classification_sevice 클래스를 호출하여 원하는 기능에 맞는 함수들을 사용
' 사용파일  : views.py
' 개발환경  : Python 3.8.3
' 이력사항
'              YYYY. MM/DD 수정자
'               1. 수정 사유: method_name {, method_name}
'/******************************************************************************

"""




import operator
import librosa # mp4 파일의 signal과 sample rate를 추출
import vamp # 음원의 signal와 sample rate로부터, 1. bothchromagram 데이터 / 2. 코드(chord) 데이터 / 3. 비트 데이터 추출

"""
1. pip install vamp
2. https://code.soundsoftware.ac.uk/projects/vamp-plugin-pack 에서 운영체제에 맞는 exe파일을 받고 Chordino and NNLS chroma 플러그인, beatRoot 플러그인 설치                       
"""

import glob
import os.path
import youtube_dl # pip install youtube_dl / pip install ffmpeg
import json

import numpy as np
import tensorflow.keras as keras #pip install tensorflow-cpu

from PIL import Image, ImageDraw, ImageFont # pip install pillow

"""
리눅스 : sudo apt-get ffmpeg
conda install -c conda-forge ffmpeg (포맷오류 날 경우)
"""

SAMPLES_TO_CONSIDER = 22050 # 오디오 샘플 값 추출시 1초에 해당하는 값.
MODEL_PATH = 'model_final_ver3.h5'



class _Chord_Classification_Service:

    model = None
    _instance = None
    _mappings = []


    def predict(self, bothchroma_list):
        """
        ' 목적 : LSTM 인공지능 모델에 오디오 파일에서 추출한 bothchroma_list 데이터를 입력하여 코드를 예측하는 함수
        ' 리턴값 : 1. 예측된 코드("label")와 코드의 출현시간값("timestamp") 리스트
        """

        prediction_list =[]
        for i in bothchroma_list:

            chromagram = np.array(i["chromagram"])[np.newaxis, ...]
            # input_shape = (1, 20, 24) (1, number of slices extract Chromagram, Chromagram)

            preditions = self.model.predict(chromagram) #[  [0.1, 0.6, 0.1, ...]  ]
            predicted_index = np.argmax(preditions)
            predicted_keyword = self._mappings[predicted_index]
            temp_dict = {"timestamp": i["timestamp"], "label": predicted_keyword}
            prediction_list.append(temp_dict)
        return prediction_list


    def add_recommend_database(self, url, json_path, audio_path):
        """
        ' 목적 : 음원의 유튜브 url으로부터 추출한, 해당 음원의 코드 정보와 url을 입력받은 json_path에 저장하는 함수 (코드 정보는 vamp 플러그인으로부터 추출)
        ' 리턴값 : 없음
        """

        # 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 파일을 제거하여 youtube_dl 오류방지
        files = glob.glob(audio_path + "/*.mp4")
        for x in files:
            if not os.path.isdir(x):
                os.remove(x)

        ydl_opts = {
            'format': 'best',
            'outtmpl': audio_path + '/%(title)s.%(ext)s',
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(audio_path + "/*.mp4")
        audio_file_name = ''

        signal, sr = 0, 0
        for x in files:
            if not os.path.isdir(x):
                filename = os.path.splitext(x)
                audio_file_name = filename[0].split(audio_path + '/')[1]
                signal, sr = librosa.load(x)
                os.remove(x)

        # load chord data from vamp plugin
        predicted_chord_list = vamp.collect(signal, sr, "nnls-chroma:chordino")


        # -----------------------추출한 데이터 형식을 다루기 쉽게 가공----------------------- #
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
        # ---------------------------------------------------------------------------- #



        with open(json_path, 'r', encoding='utf-8') as f:
            chord_list_dict = json.load(f)

        dict_key_music_name = audio_file_name

        if dict_key_music_name not in chord_list_dict:
            chord_list_dict[dict_key_music_name] = double_chord_list_with_url
            with open(json_path, "w", encoding='utf-8') as fp:
                json.dump(chord_list_dict, fp, indent=4, ensure_ascii=False)


    def LSTM_load_audio_data_from_url(self, url, audio_path):
        """
        ' 목적 : 음원의 유튜브 url로부터 음원의 코드정보(by tensorflow)와 박자정보를 추출하는 함수
        ' 리턴값 : 1. 예측된 코드와 코드의 출현시간값 리스트 / 2. 예측된 박자의 시간값 리스트 / 3. vamp 플러그인이 박자를 성공적으로 추출했는지 확인하는 Boolean값
        """

        # 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 파일을 제거하여 youtube_dl 오류방지
        files = glob.glob(audio_path + "/*.mp4")
        for x in files:
            if not os.path.isdir(x):
                os.remove(x)

        ydl_opts = {
            'format': 'best',
            'outtmpl': audio_path + '/%(title)s.%(ext)s',
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(audio_path + "/*.mp4")

        signal, sr = 0, 0
        for x in files:
            if not os.path.isdir(x):
                signal, sr = librosa.load(x)
                os.remove(x)

        # 악보 구조를 생성하는데에 필요한 박자 데이터 추출
        predicted_beat_list = vamp.collect(signal, sr, "beatroot-vamp:beatroot")
        isEmptyBeatList = False
        if(predicted_beat_list['list'] == []):
            isEmptyBeatList = True
        beat_list = []
        for i in predicted_beat_list['list']:
            beat_list.append(float(i['timestamp']))


        # ------- 코드의 출현시간과 다음 코드의 출현시간 사이의 구간의 음원샘플을 이용해 LSTM 인공지능 모델에 입력할 음원 특성값(chromagram)을 추출 --------- #
        bothchroma_list = []

        chord_with_timestamp_list = vamp.collect(signal, sr, "nnls-chroma:chordino")
        chord_timestamp_list = []
        for i in chord_with_timestamp_list['list']:

            if i['label'] != 'N': # 코드가 추출되지 않는 부분의 코드 label은 None을 의미하는 N으로 표시되기때문에 해당 부분은 활용하지 않는다.
                i['timestamp'] = float(i['timestamp'])
                chord_timestamp_list.append(i['timestamp'])


        for idx in range(len(chord_timestamp_list) - 1):

            start = int(chord_timestamp_list[idx] * SAMPLES_TO_CONSIDER)
            end = int(chord_timestamp_list[idx + 1] * SAMPLES_TO_CONSIDER)

            # 시간 간격에 따라 추출되는 (n,24)형식의 chromagram 데이터를 (20,24)로 맞추는 작업
            interval_chroma_list = []
            if(end - start >= 40960): # signal 간격이 40960일때 (20,24)의 chromagram 데이터가 추출됨
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

            temp_dict = {"timestamp": chord_timestamp_list[idx], "chromagram": interval_chroma_list}
            bothchroma_list.append(temp_dict)

        # 마지막 코드(chord)의 특성값 추출 시간간격 설정
        start = int(chord_timestamp_list[-1] * SAMPLES_TO_CONSIDER)
        last_interval_signal = signal[start:]
        interval_chroma_list = vamp.collect(last_interval_signal, sr, "nnls-chroma:nnls-chroma", output="bothchroma")
        interval_chroma_list = list(interval_chroma_list['matrix'])[1].tolist()
        if (len(interval_chroma_list) > 20):
            interval_chroma_list = interval_chroma_list[:21]
            if (len(interval_chroma_list) == 21):
                interval_chroma_list.pop()  # 간혹 21 나오는 경우가 있어서 끝값 삭제
        elif (len(interval_chroma_list) < 20):
            while (len(interval_chroma_list) != 20):
                interval_chroma_list.append(interval_chroma_list[-1])

        temp_dict = {"timestamp": chord_timestamp_list[-1], "chromagram": interval_chroma_list}
        bothchroma_list.append(temp_dict)
        # ------------------------------------------------------------------------------------- #

        LSTM_model_predicted_chord_list = self.predict(bothchroma_list)

        return LSTM_model_predicted_chord_list, beat_list, isEmptyBeatList


    def load_audio_data_from_url(self, url, audio_path):
        """
        ' 목적 : 음원의 유튜브 url로부터 음원의 코드정보(by vamp plugin)와 박자정보를 추출하는 함수
        ' 리턴값 : 1. 예측된 코드와 코드의 출현시간값 리스트 / 2. 예측된 박자의 시간값 리스트 / 3. 다운로드 받은 오디오 파일명 /  4. vamp 플러그인이 박자를 성공적으로 추출했는지 확인하는 Boolean값
        """

        # 사용자가 앱을 수행하다 중단했을시, 제거되지 않고 남아있는 파일을 제거하여 youtube_dl 오류방지
        files = glob.glob(audio_path + "/*.mp4")
        for x in files:
            if not os.path.isdir(x):
                os.remove(x)

        ydl_opts = {
            'format': 'best',
            'outtmpl': audio_path + '/%(title)s.%(ext)s',
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob(audio_path + "/*.mp4")
        audio_file_name = ''

        signal, sr = 0, 0
        for x in files:
            if not os.path.isdir(x):
                filename = os.path.splitext(x)
                audio_file_name = filename[0].split(audio_path + '/')[1]
                signal, sr = librosa.load(x)
                os.remove(x)

        # 악보 구조를 생성하는데에 필요한 박자 데이터 추출
        predicted_beat_list = vamp.collect(signal, sr, "beatroot-vamp:beatroot")
        isEmptyBeatList = False
        if (predicted_beat_list['list'] == []):
            isEmptyBeatList = True

        # 악보를 생성하는데에 필요한 코드 데이터 추출
        predicted_chord_list = vamp.collect(signal, sr, "nnls-chroma:chordino")

        chord_list = []
        for i in predicted_chord_list['list']:
            i['timestamp'] = float(i['timestamp'])
            chord_list.append(i)

        beat_list = []
        for i in predicted_beat_list['list']:
            beat_list.append(float(i['timestamp']))


        return chord_list, beat_list, audio_file_name, isEmptyBeatList



    def make_music_sheet(self, url, title, isLSTM, audio_path):
        """
        ' 목적 : 음원의 유튜브 url로부터 해당 음원의 악보 이미지 파일을 생성하고 저장하는 함수
        ' 리턴값 : 저장한 악보 이미지 파일명
        """

        chord_list = []
        beat_list = []
        isEmptyBeatList = False

        if(isLSTM):
            chord_list, beat_list, isEmptyBeatList = self.LSTM_load_audio_data_from_url(url, audio_path)
        else:
            chord_list, beat_list, audio_file_name, isEmptyBeatList = self.load_audio_data_from_url(url, audio_path)

        text = ''
        sheet_width = 0
        sheet_height = 0


        if(not isEmptyBeatList):
            # -------------------------------- 악보 한줄에 16 박자가 들어가도록 코드정보 배열 -------------------------- #

            # for문을 돌다가 마지막 element에 도달하기 전에 끊기지 않게 하기
            while ((len(beat_list) + 6) % 16 != 0):
                beat_list.append(beat_list[-1])
            beat_list.append(beat_list[-1])

            longest_line_length = len(title)

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

            # ------------------------------------------------------------------------------------------------------ #
        else:
            # ---------------- 박자 정보 추출이 안된 경우 악보 한줄에 4개의 코드가 들어가도록 코드정보를 배열 -------------------- #

            longest_line_length = len(title)

            text += title
            text += '\n\n\n'

            total_chord_cnt = 0
            beat_flag = 0

            isFourCnt = 0


            for chord in chord_list:

                isFourCnt += 1
                if isFourCnt == 4:
                    isFourCnt = 0
                    text += '\n\n'
                    text += chord['label'] + '  '
                else:
                    text += chord['label'] + '  '

            total_chord_cnt = len(chord_list)

            text_list = text.split('\n\n')
            for text_line in text_list:
                if longest_line_length < len(text_line):
                    longest_line_length = len(text_line)


            sheet_height = len(text.split('\n\n'))
            sheet_width = longest_line_length * 35

            # 한글 제목이 너무 긴경우 이미지 파일 크기가 안맞기 때문에 다른 기준으로 조정
            sheet_width_alt = int(250 * total_chord_cnt / sheet_height)
            if sheet_height * 90 / sheet_width_alt > 6:
                sheet_width_alt += int(sheet_height * 90 / sheet_width_alt) * 23
            if (sheet_width_alt > sheet_width):
                sheet_width = sheet_width_alt

            # -------------------------------------------------------------------------------------------------------- #


        font = ImageFont.truetype('C:/Windows/Fonts/batang.ttc', 45) # 주의! 운영체제 별로 폰트경로 재설정 필요
        img = Image.new(mode='RGB', size=(sheet_width, sheet_height * 90), color='#FFF')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), text, font=font, fill='#000')

        music_sheet_path = 'music_sheet_img/' + title

        if(not isLSTM):
            music_sheet_path += '_quick'

        music_sheet_path += '.png'

        img.save(music_sheet_path, format='PNG')

        return music_sheet_path




    def get_top_three_similar_chord_music(self, url, music_subject, json_path, audio_path):
        """
        ' 목적 : 음원의 유튜브 url로부터 얻은 연속코드와 단일코드 정보를 기준으로 가장 유사한 3가지 음악을 찾아내고 해당 정보를 저장하는 함수
        ' 리턴값 : 1. 연속코드기반 탑3 추천 리스트 / 2. 단일코드기반 탑3 추천 리스트
        """

        chord_list_with_timestamp, beat_list, audio_file_name, isEmptyBeatList = self.load_audio_data_from_url(url, audio_path)

        # 모든 코드정보가 포함된 추천음악 리스트를 저장한 json 데이터 불러오기
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # --------------------------------------- 1. 연속코드 비교 --------------------------------------------- #
        # 추천기준이 되는 음원의 중복없는 코드 종류 리스트를 기준으로, json 데이터의 추천음악들의 코드 중복 횟수를 비교

        double_chord_list = []
        chord_list = []
        for i in chord_list_with_timestamp:
            chord_list.append(i['label'])
        double_chord_list = []

        for idx in range(len(chord_list) - 1):
            if chord_list[idx] != 'N' and chord_list[idx + 1] != 'N':
                double_chord = chord_list[idx] + '-' + chord_list[idx + 1]
                double_chord_list.append(double_chord)
        double_chord_name_list = list(set(double_chord_list))


        same_double_chord_cnt_dict = {}
        same_double_chord_total_cnt_dict = {}


        for key, value in data.items():
            if key == audio_file_name:
                continue  # 자기자신과는 비교 X
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

        # ---------------------------------------------------------------------------------------------------- #




        # --------------------------------------- 2. 단일코드 비교 --------------------------------------------- #
        # 추천기준이 되는 음원의 중복없는 코드 종류 리스트를 기준으로, json 데이터의 추천음악들의 코드 중복 횟수를 비교

        single_chord_list = []
        for chord in chord_list_with_timestamp:
            single_chord_list.append(chord['label'])
        single_chord_name_list = list(set(single_chord_list))

        same_single_chord_cnt_dict = {}
        same_single_chord_total_cnt_dict = {}

        for key, value in data.items():
            if key == audio_file_name:
                continue  # 자기자신과는 비교 X
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

        # ---------------------------------------------------------------------------------------------------- #


        info_data = {'double_chord': top_three_double_chord_info_dict, 'single_chord': top_three_single_chord_info_dict}

        # 한번 탑3 추천리스트를 생성한 경우, 추후에 해당 데이터를 그대로 활용하여 웹 서버 로딩시간을 줄이기 위해 json 형식으로 데이터 저장
        info_path = 'music_recommend_info/' + music_subject + '_recommend.json'
        with open(info_path, "w", encoding='utf-8') as fp:
            json.dump(info_data, fp, indent=4)

        return top_three_double_chord_info_dict, top_three_single_chord_info_dict



def Chord_Classification_Service():
    """
    ' 목적 : singleton 구조
    ' 리턴값 : Chord_Classification_Service의 인스턴스
    """

    # ensure that we only have 1 instance of CCS
    if _Chord_Classification_Service._instance is None:
        _Chord_Classification_Service._instance = _Chord_Classification_Service()
        _Chord_Classification_Service.model = keras.models.load_model(MODEL_PATH)

        # tensorflow의 LSTM 인공지능 모델의 int 출력값을 코드명에 맵핑 ( 총 105개 )
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

    return _Chord_Classification_Service._instance

