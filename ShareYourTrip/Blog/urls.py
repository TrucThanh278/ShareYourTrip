from django.urls import path, re_path, include
from rest_framework import routers
from Blog import views

r = routers.DefaultRouter()
r.register('posts', views.PostViewSet, 'posts')
r.register('hashtags', views.HashtagViewSet, 'hashtags')
r.register('users', views.UserViewSet, 'users')
r.register('comments', views.CommentViewSet, 'comments')

urlpatterns = [
    path('', include(r.urls)),
]