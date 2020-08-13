"""

'/**************************************************************************************************************
' 파일명    : prepare_dataset.py
' 작성자    : 임지백
' 목적      : 시간별 코드 데이터와 시간별 chromagram 데이터를 통해 코드별 chromagram 데이터를 만들어 json 파일로 저장해준다.
             (해당 파일에서 사용하는 chromagram 데이터는 음원의 파형을 통해 추출하는 24가지의 특성값이다)
' 사용방식  : 파일의 main문 실행시 인공지능 모델 학습에 필요한 json 파일을 저장한다.
            이때, 프로젝트 폴더에 https://www.kaggle.com/jacobvs/mcgill-billboard 해당 웹페이지에서 받은 data 폴더를 넣어준더
' 사용파일  : train_model_LSTM.py에서 이 파일에서 생성한 json 파일을 이용해 인공지능 모델 학습을 진행한다.
' 개발환경  : Python 3.7.7 / Windows10
' 이력사항
'              YYYY. MM/DD 수정자
'               1. 수정 사유: method_name {, method_name}
'/**************************************************************************************************************

"""

import csv
import numpy as np
import os.path
import json


JSON_PATH = 'data_twelve_chroma.json'


def chord_to_int(chord_name):
    """
    ' 목적 : 인공지능 학습을 위해 data 폴더에 있는 코드 정보를 int 값에 맵핑
    ' 리턴값 : 코드 이름에 따라 맵핑된 int 값 ( 0 ~ 104 ) / ( 공백음인 N 또는 X의 경우 404를 리턴하고 활용은 X )
    """
    type1 = ':maj'
    type2 = ':min'
    type3 = 'b:maj'
    type4 = 'b:min'
    type5 = '#:maj'
    type6 = '#:min'
    type7 = ':maj7'
    type8 = ':min7'
    type9 = 'b:maj7'
    type10 = 'b:min7'
    type11 = '#:maj7'
    type12 = '#:min7'
    type13 = ':7'
    type14 = 'b:7'
    type15 = '#:7'
    type_table = [type1, type2, type3, type4, type5, type6, type7, type8, type9, type10, type11, type12, type13, type14, type15]

    root_chord_list = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

    if chord_name == 'N' or chord_name == 'X':
        return 404
    for chord_num, root_chord in enumerate(root_chord_list):
        for type_num, type in enumerate(type_table):
            if root_chord + type == chord_name:
                return chord_num * 15 + type_num


def prepare_dataset(json_path):
    """
    ' 목적 : data 폴더에 위치한 데이터 파일을 통해 만든 json 파일을 json_path에 저장
    ' 리턴값 : 없음
    """
    data = {
        "labels": [],
        "Chromagram_bundles": [],
    }

    chroma_and_start_time = {
        # 키값은 각각의 폴더명
    }
    chord_and_interval_time = {
        # 키값은 각각의 폴더명
    }


    path_metadata = './data/metadata/metadata'
    file_metadata = '/bothchroma.csv'
    path_annotations = './data/annotations/annotations/'
    file_annotations = '/majmin.lab'


    for folder_num in range(3, 1301): # 음원의 데이터가 들어있는 폴더명은 0003 ~ 1300
        if (folder_num < 10):
            common_path_variable = '/000' + str(folder_num)
        elif (folder_num < 100):
            common_path_variable = '/00' + str(folder_num)
        elif (folder_num < 1000):
            common_path_variable = '/0' + str(folder_num)
        else:
            common_path_variable = '/' + str(folder_num)

        complete_path_metadata = path_metadata + common_path_variable + file_metadata
        complete_path_annotations = path_annotations + common_path_variable + file_annotations

        # 파일이 존재하는지 체크
        if (os.path.isfile(complete_path_metadata)):
            pass
        else:
            continue

        chroma_and_start_time[str(folder_num)] = []
        chord_and_interval_time[str(folder_num)] = []

        # chromagram 데이터 불러오기
        with open(complete_path_metadata, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)

            #초반의 의미없는 chromagram 값들을 패스
            for _ in range(20):
                next(reader)

            for starting_time_and_chroma in reader:
                del starting_time_and_chroma[0] # 빈 값 삭제
                chroma_and_start_time[str(folder_num)].append(list(map(float, starting_time_and_chroma)))  # string을 float으로 저장

        # 코드 데이터 불러오기
        with open(complete_path_annotations, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for interval_time_and_chord in reader:
                if (interval_time_and_chord != []):
                    chord_data_list = interval_time_and_chord[0].split('\t')
                    chord_name = chord_data_list[2]
                    if  chord_name != 'N' and chord_name != 'X':
                        chord_data_list[2] = chord_to_int(chord_name)  # 코드이름 -> 코드이름에 맵핑된 int값
                        chord_data_list[1] = float(chord_data_list[1]) # 코드의 종료시간
                        chord_data_list[0] = float(chord_data_list[0]) # 코드의 시작시간
                        chord_and_interval_time[str(folder_num)].append(chord_data_list)

    print(len(chord_and_interval_time))
    print(len(chroma_and_start_time))

    # 인공지능 모델 학습을 위해 데이터를 (20, 24)로 묶어주기 (number of slices extract Chromagram, Chromagram)
    for key, value in chroma_and_start_time.items():
        for chord_list in chord_and_interval_time[key]:
            chroma_bundle = []
            num_flag = 0
            for chroma_list in value:
                if num_flag >= 20:
                    break
                if chroma_list[0] >= chord_list[1]:
                    """
                    # chroma_list[0] : chromagram을 추출한 시작 시간 (간격은 약 0.05 초) / chroma_list[1:] : chromagram
                    # chord_list[0] : 코드의 시작시간 / chord_list[1] : 코드의 종료시간 / chord_list[2] : int 값 맵핑된 코드이름
                    """
                    break
                if chroma_list[0] >= chord_list[0] and chroma_list[0] < chord_list[1]:
                    del chroma_list[0]
                    chroma_bundle.append(chroma_list)
                    value.remove(chroma_list)
                    num_flag += 1

            if chroma_bundle != []:
                for i in range(20 - num_flag):
                    chroma_bundle.append(chroma_bundle[-1])
                if len(chroma_bundle) != 20:
                    print("문제 발생!!!")
                data["Chromagram_bundles"].append(chroma_bundle)
                data["labels"].append(chord_list[2])

    print(len(data["labels"]))
    print(data["Chromagram_bundles"][0])
    print(len(data["Chromagram_bundles"]))
    print(len(data["Chromagram_bundles"][0]))
    print(len(data["Chromagram_bundles"][0][0]))

    x_list = data["Chromagram_bundles"]
    X = np.array(x_list)
    y = np.array(data["labels"])

    print(X.shape)
    # numpy array의 shape가 분명 (N, 30, 24)로 나와야 하는데 (N, )로 나오는 경우때문에 조금 헤맸다.
    # 이 경우는 데이터의 크기가 30,24를 벗어나 있는 경우가 존재한다는 뜻이므로 데이터를 다시 재구성해주어야 한다.
    print(y.shape)

    with open(json_path, "w") as fp:
        json.dump(data, fp, indent=4)


if __name__ == "__main__":
    prepare_dataset(JSON_PATH)
