from django.shortcuts import render , redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Post, Tag, MenuDataset
from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied
from django.utils.text import slugify

from django.db.models import Q , Count

#코사인 유사도 분석
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

#open AI
from django.http import JsonResponse
import requests
import json
from django.conf import settings

import re

# Create your views here.

# 포스트 리스트
class PostList(ListView):
    model = Post
    ordering = '-pk'
    paginate_by = 5 # ListView에서 제공하는 paginate_by 이용

    #태그 List를 가져오는 함수
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.all()
        return context

# 포스트 상세
class PostDetail(DetailView):
    model = Post

    #태그 List를 가져오는 함수
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tags'] = Tag.objects.all()
        return context

# 포스트 작성
class PostCreate(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content', 'head_image']

    #작성시 자동으로 author필드를 채워주는 함수
    def form_valid(self, form):
        current_user = self.request.user
        if current_user.is_authenticated:
            form.instance.author = current_user
            response = super(PostCreate, self).form_valid(form)

            tags_str = self.request.POST.get('tags_str') # post_form.html에서 보낸 tags_str id의 post를 읽어온다.
            if tags_str:
                tags_str = tags_str.strip()  #입력받은 태그의 공백제거
                tags_str = tags_str.replace(',',';')
                tags_list = tags_str.split(';')

                for t in tags_list:
                    t = t.strip()
                    tag, is_tag_created = Tag.objects.get_or_create(name=t)

                    if is_tag_created:
                        tag.slug = slugify(t, allow_unicode=True)
                        tag.save()
                    self.object.tags.add(tag)
                return response
            else:
                return redirect('/blog/') # 인증된 사용자 아닌경우 blog 페이지로 리다이렉트

# 포스트 수정
class PostUpdate(LoginRequiredMixin, UpdateView):
    model = Post
    fields = ['title', 'content', 'head_image']

    template_name = 'blog/post_update.html' # 템플릿 지정

    # 작성자만 권한 허용
    def dispatch(self, request, *args, **kwargs):
        # 인증된 사용자 이면서 작성자인 경우만 PostUpdate를 수행할 수 있다.
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(PostUpdate, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied # 작성자 이면서 인증 사용자가 아니면 권한 없음

    # 본 게시물의 태그를 불러옴
    def get_context_data(self, **kwargs):
        context = super(PostUpdate, self).get_context_data()
        if self.object.tags.exists():
            tags_str_list = list()
            for i in self.object.tags.all():
                tags_str_list.append(i.name)
            context['tags_str_default'] = ';'.join(tags_str_list)
        return context

    #수정 페이지에서 POST 메소드로 전송한 tags_str을 처리하는 함수
    def form_valid(self, form):
        response = super(PostUpdate, self).form_valid(form)
        self.object.tags.clear()

        tags_str = self.request.POST.get('tags_str')
        if tags_str:
            tags_str = tags_str.strip()
            tags_str = tags_str.replace(',',';')
            tags_str = tags_str.split(';')

            for t in tags_str:
                t = t.strip()
                tag, is_tag_created = Tag.objects.get_or_create(name=t)
                if is_tag_created:
                    tag.slug = slugify(t, allow_unicode=True)
                    tag.save()
                self.object.tags.add(tag)
        return response

#게시글 삭제
class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/post_delete.html'  # 템플릿 지정
    success_url = reverse_lazy('blog:post_list')

    # 작성자만 권한 허용
    def dispatch(self, request, *args, **kwargs):
        # 인증된 사용자 이면서 작성자인 경우만 PostUpdate를 수행할 수 있다.
        if request.user.is_authenticated and request.user == self.get_object().author:
            return super(PostDeleteView, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied # 작성자 이면서 인증 사용자가 아니면 권한 없음

#검색
class PostSearch(PostList):
    paginate_by = None    #1

    def get_queryset(self):
        q = self.kwargs['q'] #2
        post_list = Post.objects.filter(
            Q(tags__name__contains=q) | Q(title__contains=q)  #태그만 검색 --> Q(title__contains=q) 제목 검색을 원하면 이를 추가한다
        ).distinct()   #4
        return post_list

    def get_context_data(self, **kwargs):
        context = super(PostSearch, self).get_context_data()
        q = self.kwargs['q']
        context['search_info'] = f'{q}'  # 검색 명
        context['cnt'] = f'{self.get_queryset().count()}' # 검색된 개수

        return context


# 좋아요
def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)

    if request.method == 'POST':
        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
        else:
            post.likes.add(request.user)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

# 태그(음식명) 페이지
def tag_page(request, slug):
    tag = Tag.objects.get(slug=slug)

    # post_list = tag.post_set.all()
    post_list = tag.post_set.annotate(num_likes=Count('likes')).order_by('-num_likes')

    return render(
        request,
        'blog/post_list.html',
        {
            'post_list': post_list,
            'tag': tag,
            'tags': Tag.objects.all(), #tag 리스트를 가져오는 부분
        }
    )

#open AI
#     url = "https://api.openai.com/v1/chat/completions" # gpt 엔드포인트

#chat gpt api 응답을 받아오는 부분
def show_question(request):
    return render(request, 'blog/question_form.html')

def ask_question(request):
    if request.method == "POST":
        question = request.POST.get("question")  # 사용자가 입력한 질문(음식명) 을 받아온다.
        taste = request.POST.get("taste")  # 사용자가 입력한 취향을 받아온다.

        # ChatGPT API에 요청을 보냄
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer { settings.OPENAI_API_KEY }",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": f"{question} 레시피를 알려줘. 나의 취향인 {taste}을 고려해서 자세히 답변해줘, 답변은 1인분 기준 재료(중량포함)와 상세 레시피만 해줘, (응답형식은 다음과 같이 맞춰줘 :  (음식명) \n\n 재료 : (재료 답변) \n\n 레시피 : (레시피 답변) \n\n)"}],
                "temperature": 0.7
            })
        )

        # 응답을 JSON 형식으로 파싱하여 반환
        if response.status_code == 200:
            response_data = response.json()

            ## 필요한 데이터 추출
            # print(response.json())
            completion = response_data['choices'][0]['message']['content']

            # 필요한 정보 추출
            menu_name = response_data['choices'][0]['message']['content'].split('\n\n')[0]
            # 특수기호를 포함시켜 답을 주는 경우를 대비
            pattern = re.compile(r'^\s*[\W_]+(.*?)\s*[\W_]+$') # 정규 표현식을 사용하여 특수 기호를 제거하고 양쪽 공백을 제거하는 패턴
            menu_name = pattern.sub(r'\1', menu_name)   # 정규 표현식에 맞는 부분을 찾아서 특수 기호를 제거하고 양쪽 공백을 제거함

            ingredients = response_data['choices'][0]['message']['content'].split('\n\n')[1]
            recipe = response_data['choices'][0]['message']['content'].split('\n\n')[2]
            # print(response_data['choices'][0]['message']['content'])
            # print(menu_name)
            # print(ingredients)
            # print(recipe)

            # return JsonResponse(response_data, safe=False)   # JSON응답확인용
            return render(
                request,
                'recommendations/answer_form.html',
                {
                    # "response" : completion

                    'menu_name': menu_name,
                    'ingredients': ingredients,
                    'recipe': recipe
                }
            )
        else:
            return JsonResponse({"error": "API request failed"}, status=response.status_code)
    return JsonResponse({"error": "Invalid request"}, status=400)

def post_form(request):
    content1 = request.POST.get("ingredients")
    content2 = request.POST.get("recipe")
    tags_str = request.POST.get("menu_name")

    content = str(content1) + '\n\n'  + str(content2)

    return render(
        request,
        'recommendations/post_form.html',
        {
            'content' : content,
            'tags_str' : tags_str
        }
    )


## 메뉴 추천
def input_ingredients(request):
    if request.method == 'POST':
        # 사용자가 입력한 재료를 가져오기
        ingredient1 = request.POST.get('ingredient1')
        ingredient2 = request.POST.get('ingredient2')

        # 유사도 측정을 위해 사용자가 입력한 재료를 하나의 문자열로 합치기
        user_input = f"{ingredient1} {ingredient2}"

        # 모든 메뉴의 재료정보 가져오기
        all_menus = list(MenuDataset.objects.values_list('메뉴명', '재료정보'))

        # TF-IDF 벡터화
        tfidf_vectorizer = TfidfVectorizer()
        tfidf_matrix = tfidf_vectorizer.fit_transform([menu[1] for menu in all_menus])

        # 사용자 입력 재료에 대한 TF-IDF 벡터 생성
        user_tfidf = tfidf_vectorizer.transform([user_input])

        # 사용자 입력 벡터와 모든 메뉴의 벡터를 합침
        tfidf_matrix_combined = cosine_similarity(user_tfidf, tfidf_matrix).flatten()

        # 유사도가 높은 순으로 메뉴 정렬
        recommended_menus = [(menu[0], similarity) for menu, similarity in zip(all_menus, tfidf_matrix_combined) if
                             similarity > 0.2]
        recommended_menus.sort(key=lambda x: (user_input in x[0], x[1]), reverse=True)

        # 상위 3개 메뉴만 선택
        recommended_menus = [menu for menu, _ in recommended_menus[:3]]

        # 추천 메뉴가 없으면 에러 메시지 반환
        if not recommended_menus:
            return render(request, 'recommendations/input_ingredients.html',
                          {'error_message': '해당 재료로 만들 수 있는 메뉴가 없어요.'})

        return render(request, 'recommendations/recommended_menus.html', {'recommended_menus': recommended_menus})

    return render(request, 'recommendations/input_ingredients.html')


def recipe(request, menu):
    return render(request, 'recommendations/recipe.html', {'menu': menu})