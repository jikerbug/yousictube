from django.urls import path

from . import views

app_name = 'musicboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:music_id>/', views.detail, name='detail'),
    path('music/create/', views.music_create, name='music_create'),

    path('music/modify/<int:music_id>/', views.music_modify, name='music_modify'),
    path('music/delete/<int:music_id>/', views.music_delete, name='music_delete'),

    path('comment/create/music/<int:music_id>/', views.comment_create_music, name='comment_create_music'),
    path('comment/modify/music/<int:comment_id>/', views.comment_modify_music, name='comment_modify_music'),
    path('comment/delete/music/<int:comment_id>/', views.comment_delete_music, name='comment_delete_music'),

    path('vote/music/<int:music_id>/', views.vote_music, name='vote_music'),

    #------------------------------------- 악보저장 & 음악추천 --------------------------------------------#
    path('music/download_sheet_LSTM/<int:music_id>/', views.music_download_sheet_LSTM, name='music_download_sheet_LSTM'),
    path('music/download_sheet_quick/<int:music_id>/', views.music_download_sheet_quick, name='music_download_sheet_quick'),

    path('music/recommend_music/<int:music_id>/', views.music_recommend_music, name='music_recommend_music'),
    path('music/update_recommend_music/<int:music_id>/', views.music_update_recommend_music, name='music_update_recommend_music'),

    path('music/sheet_loading/<int:music_id>/', views.music_sheet_loading, name='music_sheet_loading'),
    path('music/sheet_loading_quick/<int:music_id>/', views.music_sheet_loading_quick, name='music_sheet_loading_quick'),
    #------------------------------------- 악보저장 & 음악추천 --------------------------------------------#
]