from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('<int:pk>/', views.PostDetail.as_view()),
    path('', views.PostList.as_view(), name='post_list'),
    path('like/<int:pk>/',views.like_post, name='like_post'),
    path('tag/<str:slug>/',views.tag_page),
    path('create_post/', views.PostCreate.as_view(), name='create_post'),
    path('update_post/<int:pk>/', views.PostUpdate.as_view()),
    path('search/<str:q>/', views.PostSearch.as_view()),
    path('delete_post/<int:pk>/', views.PostDeleteView.as_view()),
    path('show_question/',views.show_question, name='show_question'),
    path('ask_question/', views.ask_question, name='ask_question'),
    path('input_ingredients/', views.input_ingredients, name='input_ingredients'),
    path('recipe/<str:menu>/', views.recipe, name='recipe'),  # 메뉴에 대한 레시피 URL
    path('post_form/', views.post_form , name='post_form'),
]