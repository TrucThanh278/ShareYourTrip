from django.db.models import Q
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, generics, parsers, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from Blog.models import Post, Hashtag, Comment, Rating, User
from Blog import serializers, paginators

# /posts/
# /posts/?q=
# /posts/{id}/
class PostViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    queryset = Post.objects.filter(active=True)
    serializer_class = serializers.PostSerializer

    def get_serializer_class(self):
        if hasattr(self, 'kwargs') and 'pk' in self.kwargs:
            # Nếu yêu cầu chứa một định danh duy nhất của đối tượng,
            # chẳng hạn như yêu cầu chi tiết (/posts/{pk}/), sử dụng PostDetailSerializer
            print('here')
            return serializers.PostDetailSerializer
        else:
            return self.serializer_class
        
    def get_permissions(self):
        if self.action in ['add_comment']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        query_set = self.queryset
        if self.action.__eq__('list'):
            q = self.request.query_params.get('q')
            if q:
                query_set = query_set.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if self.action.__eq__('retrieve'):
            query_set = Post.objects.prefetch_related('hashtags', 'user').filter(active=True)
        return query_set
    
    @action(methods=['get'], url_path='comments', detail=True)
    def get_comment(self, request, pk):
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        """
        comments = self.get_object().comment_set.select_related('user').order_by('-id')
        paginator = paginators.CommentPaginator()
        page = paginator.paginate_queryset(comments, request)
        if page is not None:
            serializer = serializers.CommentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        return Response(serializers.CommentSerializer(comments, many=True).data, status=status.HTTP_200_OK)


    @action(methods=['post'], url_path='comments', detail=True)
    def add_comment(self, request, pk):
        c = self.get_object().comment_set.create(user=request.user, content=request.data.get('content'))
        return Response(serializers.CommentSerializer(c).data, status=status.HTTP_201_CREATED)


# /hashtags/
# /hashtags/?q=
class HashtagViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Hashtag.objects.all()
    serializer_class = serializers.HashtagSerializer

    def get_queryset(self):
        query_set = self.queryset
        if self.action.__eq__('list'):
            q = self.request.query_params.get('q')
            if q:
                query_set = query_set.filter(hashtag__icontains=q)

        return query_set

# /users/: create user
# /users/current-user/: (get)
# /users/current-user/: (patch)
class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser,]

    def get_permissions(self):
        if self.action.__eq__('current_user'):
            return [permissions.IsAuthenticated()]
        else:
            return [permissions.AllowAny()]

    @action(methods=['get', 'patch'], url_path='current-user', detail=False)
    def current_user(self, request):
        user = request.user
        if request.method.__eq__('PATCH'):
            for k, v in request.data.items():
                setattr(user, k, v)
                user.password = make_password(request.data.get('password'))
                user.save()
        return Response(serializers.UserSerializer(user).data)
