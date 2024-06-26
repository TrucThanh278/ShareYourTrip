from django.urls import path, re_path, include
from rest_framework import routers
from Blog import views

r = routers.DefaultRouter()
r.register('posts', views.PostViewSet, 'posts')
r.register('hashtags', views.HashtagViewSet, 'hashtags')
r.register('users', views.UserViewSet, 'users')
r.register('comments', views.CommentViewSet, 'comments')
r.register('group', views.GroupViewSet, 'group')
r.register('report', views.ReportViewSet, 'report')
r.register('follow', views.FollowViewSet, 'follow')
r.register('images', views.ImageViewSet, 'images')
r.register('rating', views.RatingViewSet, 'rating')


urlpatterns = [
    path('', include(r.urls)),
    path('api/logout', views.logout, name='logout'),
]