from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class MusicPost(models.Model):
    objects = models.Manager()

    subject = models.CharField(max_length=200)
    url = models.URLField()
    create_date = models.DateTimeField()

    # -------------------------------------[edited]--------------------------------------------#
    isAdded = models.BooleanField(default=False)
    # -------------------------------------[edited]--------------------------------------------#

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='author_music')
    modify_date = models.DateTimeField(null=True, blank=True)

    voter = models.ManyToManyField(User, related_name='voter_question')  # 추천한 사람
    hit = models.IntegerField(default=0) # 조회수

    def __str__(self):
        return self.subject

class Comment(models.Model):
    objects = models.Manager()

    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    create_date = models.DateTimeField()
    modify_date = models.DateTimeField(null=True, blank=True)
    music = models.ForeignKey(MusicPost, null=True, blank=True, on_delete=models.CASCADE)