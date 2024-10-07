from django.contrib import admin
from .models import Post, Tag

# Register your models here.
admin.site.register(Post)

# tag
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name', )}

admin.site.register(Tag, TagAdmin)