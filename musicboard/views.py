import json
from wsgiref.util import FileWrapper


from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
#-------------------------------------[edited]--------------------------------------------#
from .chord_classification_service import Chord_Classification_Service
from django.http import HttpResponse, JsonResponse
import os
import urllib
import mimetypes
#-------------------------------------[edited]--------------------------------------------#


from .models import MusicPost, Comment
from .forms import MusicForm, CommentForm


# Create your views here.

JSON_PATH = 'data_big.json'
def index(request):
    """
    musicboard 목록 출력
    """
    # 입력 파라미터
    page = request.GET.get('page', '1')  # 페이지
    kw = request.GET.get('kw', '')  # 검색어
    so = request.GET.get('so', 'recent')  # 정렬기준

    # 정렬
    if so == 'recommend':
        music_list = MusicPost.objects.annotate(num_voter=Count('voter')).order_by('-num_voter', '-create_date')
    elif so == 'hits':
        music_list = MusicPost.objects.order_by('-hit')
    else:  # recent
        music_list = MusicPost.objects.order_by('-create_date')

    # 검색
    if kw:
        music_list = music_list.filter(
            Q(subject__icontains=kw) |  # 제목검색
            Q(author__username__icontains=kw)  # 글쓴이검색
        ).distinct()

    # 페이징처리
    paginator = Paginator(music_list, 10)  # 페이지당 10개씩 보여주기
    page_obj = paginator.get_page(page)

    context = {'music_list': page_obj, 'page': page, 'kw': kw, 'so': so}
    return render(request, 'musicboard/music_list.html', context)


def detail(request, music_id):
    """
    musicboard 내용 출력
    """
    music = get_object_or_404(MusicPost, pk=music_id)

    # 조회수 증가
    music.hit = music.hit + 1
    music.save()

    # iframe용 URL로 변경
    realUrl = str(music.url)
    iframeUrl = realUrl.replace("watch?v=", "embed/")
    if realUrl == iframeUrl:
        iframeUrl = realUrl.replace("youtu.be/", "www.youtube.com/embed/")

    context = {'music': music, 'iframeUrl': iframeUrl}
    return render(request, 'musicboard/music_detail.html', context)


@login_required(login_url='common:login')
def music_create(request):
    """
    musicboard 음악 등록
    """
    if request.method == 'POST':
        form = MusicForm(request.POST)
        if form.is_valid():
            music = form.save(commit=False)
            music.author = request.user  # 추가한 속성 author 적용
            music.create_date = timezone.now()
            music.save()


            return redirect('musicboard:index')
    else:
        form = MusicForm()
    context = {'form': form}
    return render(request, 'musicboard/music_form.html', context)


@login_required(login_url='common:login')
def music_modify(request, music_id):
    """
    musicboard 음악 수정
    """
    music = get_object_or_404(MusicPost, pk=music_id)
    if request.user != music.author:
        messages.error(request, "You don't have the right to modify it.")
        return redirect('musicboard:detail', music_id=music.id)

    if request.method == "POST":
        form = MusicForm(request.POST, instance=music)
        if form.is_valid():
            music = form.save(commit=False)
            music.author = request.user
            music.modify_date = timezone.now()  # 수정일시 저장
            music.save()
            return redirect('musicboard:detail', music_id=music.id)
    else:
        form = MusicForm(instance=music)
    context = {'form': form}
    return render(request, 'musicboard/music_form.html', context)


@login_required(login_url='common:login')
def music_delete(request, music_id):
    """
    musicboard 음악 삭제
    """
    music = get_object_or_404(MusicPost, pk=music_id)
    if request.user != music.author:
        messages.error(request, "You don't have the right to delete it.")
        return redirect('musicboard:detail', music_id=music.id)
    music.delete()
    return redirect('musicboard:index')


@login_required(login_url='common:login')
def comment_create_music(request, music_id):
    """
    musicboard 댓글 등록
    """
    music = get_object_or_404(MusicPost, pk=music_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.create_date = timezone.now()
            comment.music = music
            comment.save()
            return redirect('musicboard:detail', music_id=music.id)
    else:
        form = CommentForm()
    context = {'form': form}
    return render(request, 'musicboard/comment_form.html', context)


@login_required(login_url='common:login')
def comment_modify_music(request, comment_id):
    """
    musicboard 댓글 수정
    """
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.author:
        messages.error(request, "You don't have the right to modify it.")
        return redirect('musicboard:detail', music_id=comment.music.id)

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.modify_date = timezone.now()
            comment.save()
            return redirect('musicboard:detail', music_id=comment.music.id)
    else:
        form = CommentForm(instance=comment)
    context = {'form': form}
    return render(request, 'musicboard/comment_form.html', context)


@login_required(login_url='common:login')
def comment_delete_music(request, comment_id):
    """
    musicboard 댓글 삭제
    """
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user != comment.author:
        messages.error(request, "You don't have the right to delete it.")
        return redirect('musicboard:detail', music_id=comment.music_id)
    else:
        comment.delete()
    return redirect('musicboard:detail', music_id=comment.music_id)


@login_required(login_url='common:login')
def vote_music(request, music_id):
    """
    musicboard 추천 등록
    """
    music = get_object_or_404(MusicPost, pk=music_id)
    if request.user == music.author:
        messages.error(request, "You can't recommend what you wrote.")
    else:
        music.voter.add(request.user)
    return redirect('musicboard:detail', music_id=music.id)

#-------------------------------------[edited]--------------------------------------------#
def music_download_sheet(request, music_id):

    music = get_object_or_404(MusicPost, pk=music_id)
    ccs = Chord_Classification_Service()

    music_sheet_path =''
    music_sheet_name =''
    if(not os.path.isfile('music_sheet_img/' + music.subject + ".png")):
        music_sheet_path = ccs.make_music_sheet(music.url, music.subject, 'audio_download/make_sheet')
        music_sheet_name = music.subject + ".png"
    else:
        music_sheet_path = 'music_sheet_img/' + music.subject + ".png"
        music_sheet_name = music.subject + ".png"

    print(21231)

    file_name = urllib.parse.quote(music_sheet_name.encode('utf-8'))



    if os.path.exists(music_sheet_path):
        with open(music_sheet_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(music_sheet_path)[0])
            response['Content-Disposition'] = 'attachment;filename*=UTF-8\'\'%s' % file_name
            return response


def music_recommend_music(request, music_id):

    music = get_object_or_404(MusicPost, pk=music_id)
    ccs = Chord_Classification_Service()

    info_path = 'music_recommend_info/' + music.subject + "_recommend.json"
    double_chord_recommend_dict = {}
    single_chord_recommend_dict = {}
    if (not os.path.isfile(info_path)):
        double_chord_recommend_dict, single_chord_recommend_dict = ccs.get_top_three_similar_chord_music(music.url, music.subject, JSON_PATH,
                                                                                                         'audio_download/recommend_music')
    else:
        with open(info_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            double_chord_recommend_dict = data['double_chord']
            single_chord_recommend_dict = data['single_chord']

    ranking_flag = 0
    for idx, value in enumerate( double_chord_recommend_dict.values()):
        value['iframe_url'] = value['url'].replace("watch?v=", "embed/")
        if idx == 0:
            value['ranking'] = '1st'
        elif idx == 1:
            value['ranking'] = '2nd'
        else:
            value['ranking'] = '3rd'

    for idx, value in enumerate(single_chord_recommend_dict.values()):
        value['iframe_url'] = value['url'].replace("watch?v=", "embed/")
        if idx == 0:
            value['ranking'] = '1st'
        elif idx == 1:
            value['ranking'] = '2nd'
        else:
            value['ranking'] = '3rd'


    context = {'music' : music, 'double_chord_recommend_dict': double_chord_recommend_dict, 'single_chord_recommend_dict': single_chord_recommend_dict}
    return render(request, 'musicboard/music_recommend.html', context)


def music_update_recommend_music(request, music_id):
    print('test')
    music = get_object_or_404(MusicPost, pk=music_id)
    ccs = Chord_Classification_Service()

    double_chord_recommend_dict, single_chord_recommend_dict = ccs.get_top_three_similar_chord_music(music.url,
                                                                                                         music.subject,
                                                                                                         JSON_PATH,
                                                                                                     'audio_download/update_recommend_music')

    if(not music.isAdded):
        ccs.add_recommend_database(music.url, JSON_PATH, 'audio_download/update_recommend_music')
        music.isAdded = True
        music.save()

    for value in double_chord_recommend_dict.values():
        value['iframe_url'] = value['url'].replace("watch?v=", "embed/")

    for value in single_chord_recommend_dict.values():
        value['iframe_url'] = value['url'].replace("watch?v=", "embed/")

    context = {'music': music, 'double_chord_recommend_dict': double_chord_recommend_dict,
               'single_chord_recommend_dict': single_chord_recommend_dict}
    return render(request, 'musicboard/music_recommend.html', context)




def music_sheet_loading(request, music_id):
    """
    musicboard 내용 출력
    """
    music = get_object_or_404(MusicPost, pk=music_id)


    # iframe용 URL로 변경
    realUrl = str(music.url)
    iframeUrl = realUrl.replace("watch?v=", "embed/")
    if realUrl == iframeUrl:
        iframeUrl = realUrl.replace("youtu.be/", "www.youtube.com/embed/")

    context = {'music': music, 'iframeUrl': iframeUrl}
    return render(request, 'musicboard/music_sheet_loading.html', context)




#-------------------------------------[edited]--------------------------------------------#