from django.db.models import Q
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, generics, parsers, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from Blog.models import Post, Hashtag, Comment, Rating, User, Like, Follow, Report, Group, Image
from Blog import serializers, paginators, perms
from Blog.perms import IsAdmin, IsUser
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.db.models import Avg
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied



# /posts/
# /posts/?q=
# /posts/{id}/
# /post/{id}/comments/ (post)

class PostViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView, generics.CreateAPIView):
    queryset = Post.objects.filter(active=True)
    serializer_class = serializers.PostSerializer
    pagination_class = paginators.PostPaginator

    def get_serializer_class(self):
        if hasattr(self, 'kwargs') and 'pk' in self.kwargs:
            # Nếu yêu cầu chứa một định danh duy nhất của đối tượng,
            # chẳng hạn như yêu cầu chi tiết (/posts/{pk}/), sử dụng PostDetailSerializer
            return serializers.PostDetailSerializer
        else:
            return self.serializer_class


    def get_queryset(self):
        query_set = self.queryset
        if self.action == 'list':
            q = self.request.query_params.get('q')
            if q:
                query_set = query_set.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if self.action == 'retrieve':
            query_set = Post.objects.prefetch_related('hashtags', 'user').filter(active=True)
        return query_set

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied()
        serializer.save(user=self.request.user)

    @action(methods=['get', 'post'], url_path='comments', detail=True)
    def comment_handle(self, request, pk):
        if request.method.__eq__('POST'):
            if not request.user.is_authenticated:
                raise PermissionDenied()
            c = self.get_object().comment_set.create(user=request.user, content=request.data.get('content'))
            return Response(serializers.CommentSerializer(c).data, status=status.HTTP_201_CREATED)
        elif request.method.__eq__('GET'):
            comments = self.get_object().comment_set.order_by('-id').filter(parent_comment__isnull=True).select_related('user')
            paginator = paginators.CommentPaginator()
            page = paginator.paginate_queryset(comments, request)
            if page is not None:
                serializer = serializers.CommentSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            return Response(serializers.CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='images', detail=True)
    def images_handle(self, request, pk):
            images = self.get_object().images.order_by('-id')
            return Response(serializers.ImageSerializer(images, many=True).data, status=status.HTTP_200_OK)

# /hashtags/
# /hashtags/?q=
class HashtagViewSet(viewsets.ViewSet, generics.ListAPIView, generics.CreateAPIView):
    queryset = Hashtag.objects.all()
    serializer_class = serializers.HashtagSerializer

    def get_queryset(self):
        query_set = self.queryset
        if self.action == 'list':
            q = self.request.query_params.get('q')
            if q:
                query_set = query_set.filter(hashtag__icontains=q)
        return query_set


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser,]

    def get_permissions(self):
        if self.action.__eq__('current_user'):
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.AllowAny()]
        
    def get_queryset(self):
        query_set = self.queryset
        if self.action.__eq__('retrieve'):
            query_set = User.objects
        return query_set

    @action(methods=['get', 'patch'], url_path='current-user', detail=False)
    def current_user(self, request):
        user = request.user
        if request.method.__eq__('PATCH'):
            for k, v in request.data.items():
                setattr(user, k, v)
                user.password = make_password(request.data.get('password'))
                user.save()
        return Response(serializers.UserSerializer(user).data)
    
    
class CommentViewSet(viewsets.ViewSet, generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = serializers.CommentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(parent_comment__isnull=True).order_by('-created_date')
        post_id = self.request.query_params.get('postId')
        if post_id:
            queryset = queryset.filter(post_id=post_id, parent_comment__isnull=True).order_by('-created_date')
        return queryset
    
    def get_permissions(self):
        if self.action.__eq__('list'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def delete(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.user == request.user:
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.user == request.user:
            comment.content = request.data.get('content')
            comment.save()
            return Response(serializers.CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

class GroupViewSet(viewsets.ModelViewSet, generics.CreateAPIView, generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer
    permission_classes = [permissions.IsAuthenticated]  # Ensure the user is authenticated

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(reporter=self.request.user)
        else:
            raise serializers.ValidationError("You must be logged in to report a user.")

class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    serializer_class = serializers.FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = serializers.ImageSerializer
    def perform_create(self, serializer):
        serializer.save(post=self.request.user.post_set.first())