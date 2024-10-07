from django.db import models
from django.contrib.auth.models import User

# Tag
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=200, unique=True, allow_unicode=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/blog/tag/{self.slug}/'

class Post(models.Model):
    title = models.CharField(max_length=30)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    likes = models.ManyToManyField(User, related_name='like_post', blank=True)

    tags = models.ManyToManyField(Tag, blank=True)
    # tags = models.ManyToManyField(Tag, blank=True, on_delete=models.PROTECT)

    head_image = models.ImageField(upload_to='blog/images/%Y/%m/%d/', blank=True)

    def __str__(self):
        return f'[{self.pk}]{self.title}] :: {self.author}'

    def get_absolute_url(self):
        return f'/blog/{ self.pk }/'

    def total_count(self):
        return self.likes.count()

# 메뉴 데이터
class MenuDataset(models.Model):
    번호 = models.IntegerField(blank=True, null=True)
    메뉴명 = models.TextField(blank=True, null=True)
    재료정보 = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'menu_dataset'