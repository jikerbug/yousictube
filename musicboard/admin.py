from django.contrib import admin
from .models import MusicPost

# Register your models here.
class MusicPostAdmin(admin.ModelAdmin):
    search_fields = ['subject']

admin.site.register(MusicPost, MusicPostAdmin)