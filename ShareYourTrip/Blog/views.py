from django.db.models import Q
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, generics, parsers, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from Blog.models import Post, Hashtag, Comment, Rating, User, Like, Follow
from Blog import serializers, paginators, perms
from Blog.perms import IsAdmin, IsUser
from django.contrib.auth.models import Group
from django.http import JsonResponse
from django.db.models import Avg
from django.shortcuts import get_object_or_404

# /posts/
# /posts/?q=
# /posts/{id}/
# /post/{id}/comments/ (post)
class PostViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Post.objects.filter(active=True)
    serializer_class = serializers.PostSerializer

    def get_serializer_class(self):
        if hasattr(self, 'kwargs') and 'pk' in self.kwargs:
            return serializers.PostDetailSerializer
        return self.serializer_class

    def get_permissions(self):
        if self.action in ['comment_handle', 'like', 'rating', 'add_hashtag']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        query_set = self.queryset
        if self.action == 'list':
            q = self.request.query_params.get('q')
            if q:
                query_set = query_set.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if self.action == 'retrieve':
            query_set = Post.objects.prefetch_related('hashtags', 'user').filter(active=True)
        return query_set

    @action(methods=['get', 'post'], url_path='comments', detail=True)
    def comment_handle(self, request, pk):
        post = self.get_object()
        if request.method == 'POST':
            c = post.comment_set.create(user=request.user, content=request.data.get('content'))
            return Response(serializers.CommentSerializer(c).data, status=status.HTTP_201_CREATED)
        elif request.method == 'GET':
            comments = post.comment_set.order_by('-id')
            paginator = paginators.CommentPaginator()
            page = paginator.paginate_queryset(comments, request)
            if page is not None:
                serializer = serializers.CommentSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            return Response(serializers.CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='like', detail=True)
    def like(self, request, pk):
        post = self.get_object()
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.active = not like.active
            like.save()
        return Response(serializers.PostDetailSerializer(post, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='rating', detail=True)
    def rating(self, request, pk):
        post = self.get_object()
        rating, created = Rating.objects.get_or_create(user=request.user, post=post)
        if not created:
            rating.active = not rating.active
            rating.save()
        return Response(serializers.PostDetailSerializer(post, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    @action(methods=['post'], url_path='hashtag', detail=True)
    def add_hashtag(self, request, pk):
        post = self.get_object()
        hashtag = Hashtag.objects.get_or_create(hashtag=request.data.get('hashtag'))[0]
        post.hashtags.add(hashtag)
        return Response(serializers.HashtagSerializer(hashtag).data, status=status.HTTP_201_CREATED)




# /hashtags/
# /hashtags/?q=
class HashtagViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Hashtag.objects.all()
    serializer_class = serializers.HashtagSerializer

    def get_queryset(self):
        query_set = self.queryset
        if self.action == 'list':
            q = self.request.query_params.get('q')
            if q:
                query_set = query_set.filter(hashtag__icontains=q)
        return query_set


# /users/: create user
# /users/current-user/: (get, patch)
class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True).all()
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser]

    def get_permissions(self):
        if self.action == 'current_user' or self.action == 'update_profile':
            return [permissions.IsAuthenticated()]
        elif self.action == 'register':
            if self.request.data.get('role') == 'patient':
                return [permissions.AllowAny()]
            else:
                return [IsAdmin()]
        else:
            return [permissions.AllowAny()]

    @action(methods=['post'], detail=False, url_path='register', url_name='register')
    def register(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data.get('role')
        user = serializer.save()
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)



    @action(methods=['get'], detail=False, url_path='profile', url_name='profile')
    def profile(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication credentials were not provided.'},
                            status=status.HTTP_401_UNAUTHORIZED)

        user = request.user
        serializer = self.get_serializer(user)

        followers_count = user.followers.count()
        following_count = user.following.count()
        average_rating = user.received_ratings.aggregate(Avg('stars'))['stars__avg']
        average_rating = round(average_rating, 2) if average_rating else 0

        data = serializer.data
        data['followers_count'] = followers_count
        data['following_count'] = following_count
        data['average_rating'] = average_rating

        return Response(data)

    @action(methods=['patch'], detail=False, url_path='update-profile', url_name='update-profile')
    def update_profile(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if 'password' in serializer.validated_data:
            serializer.validated_data['password'] = make_password(serializer.validated_data['password'])

        user = serializer.save()

        role = request.data.get('role')
        if role and role != user.role:
            if IsAdmin().has_permission(request, self):
                user.groups.clear()
                group, _ = Group.objects.get_or_create(name=role)
                user.groups.add(group)
            else:
                return Response({'error': 'You are not allowed to update role of this user'},
                                status=status.HTTP_403_FORBIDDEN)

        return Response(self.get_serializer(user).data, status=status.HTTP_200_OK)

    @action(methods=['get', 'patch'], detail=False, url_path='current-user')
    def current_user(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            if 'password' in serializer.validated_data:
                serializer.validated_data['password'] = make_password(serializer.validated_data['password'])
            serializer.save()
            return Response(serializer.data)
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(methods=['get'], url_path='average-rating', detail=True, permission_classes=[permissions.AllowAny])
    def user_average_rating(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs.get('pk'))
        user_ratings = Rating.objects.filter(user=user)
        if user_ratings.exists():
            average_rating = user_ratings.aggregate(Avg('stars'))['stars__avg']
            return Response({'average_rating': average_rating})
        else:
            return Response({'error': 'User has no ratings'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        queryset = User.objects.filter(is_active=True).all()
        serializer = serializers.UserSerializer(queryset, many=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializers.UserSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


# /comments/{id}/ (delete, patch)
class CommentViewSet(viewsets.ViewSet, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Comment.objects.all()
    serializer_class = serializers.CommentSerializer
    permission_classes = [perms.OwnerAuthenticated]


# /ratings/{id}/ (delete, patch)
class RatingViewSet(viewsets.ViewSet, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Rating.objects.all()
    serializer_class = serializers.RatingSerializer
    permission_classes = [perms.OwnerAuthenticated]

class FollowListCreateAPIView(generics.ListCreateAPIView):
    queryset = Follow.objects.all()
    serializer_class = serializers.FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user)

class FollowRetrieveDestroyAPIView(generics.RetrieveDestroyAPIView):
    queryset = Follow.objects.all()
    serializer_class = serializers.FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user)

    def delete(self, request, *args, **kwargs):
        follow = self.get_object()
        if follow.follower != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().delete(request, *args, **kwargs)