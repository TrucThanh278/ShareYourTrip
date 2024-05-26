from django.urls import path, re_path, include
from rest_framework import routers
from Blog import views
from .views import FollowListCreateAPIView, FollowRetrieveDestroyAPIView

r = routers.DefaultRouter()
r.register('posts', views.PostViewSet, 'posts')
r.register('hashtags', views.HashtagViewSet, 'hashtags')
r.register('users', views.UserViewSet, 'users')
r.register(r'comments', views.CommentViewSet, basename='comment')
r.register(r'ratings', views.RatingViewSet, basename='rating')
urlpatterns = [
    path('', include(r.urls)),
    path('follows/', FollowListCreateAPIView.as_view(), name='follow-list-create'),
    path('follows/<int:pk>/', FollowRetrieveDestroyAPIView.as_view(), name='follow-retrieve-destroy'),
]