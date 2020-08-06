from django import forms
from musicboard.models import MusicPost, Comment

class MusicForm(forms.ModelForm):
    class Meta:
        model = MusicPost
        fields = ['subject', 'url']
        labels = {
            'subject': 'Title',
            'url': 'URL',
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        labels = {
            'content': 'Comment content',
        }