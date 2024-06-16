from django.db.models import Q
from django.contrib.auth.hashers import make_password
from rest_framework import viewsets, generics, parsers, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from Blog.models import Post, Hashtag, Comment, Rating, User, Like, Follow, Report, Group, Image
from Blog import serializers, paginators, perms
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework import status
from oauth2_provider.models import AccessToken
from Blog.serializers import CommentSerializer


@api_view(['DELETE'])
def logout(request):
    try:
        token = request.headers.get('Authorization').split(' ')[1]
        access_token = AccessToken.objects.get(token=token)
        access_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except AccessToken.DoesNotExist:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                query_set = query_set.filter(
                    Q(title__icontains=q) | Q(description__icontains=q) | Q(starting_point__icontains=q) | Q(
                        end_point__icontains=q))
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
            content = request.data.get('content')
            parent_comment_id = request.data.get('parent_comment')
            parent_comment = None
            if parent_comment_id:
                try:
                    parent_comment = Comment.objects.get(id=parent_comment_id)
                except Comment.DoesNotExist:
                    return Response({"detail": "Parent comment not found."}, status=status.HTTP_400_BAD_REQUEST)
            # Tạo comment mới với các thuộc tính cần thiết
            comment = Comment.objects.create(
                user=request.user,
                post=self.get_object(),
                content=content,
                parent_comment=parent_comment
            )
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        elif request.method.__eq__('GET'):
            comments = self.get_object().comment_set.order_by('-id').filter(parent_comment__isnull=True).select_related(
                'user')
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

    @action(methods=['get'], detail=True, url_path='average_rating')
    def average_rating(self, request, pk=None):
        post = self.get_object()
        ratings = post.ratings.all()  # Sử dụng related_name 'ratings'
        if not ratings.exists():
            return Response({'average_rating': 0}, status=status.HTTP_200_OK)
        average = sum(rating.stars for rating in ratings) / ratings.count()  # Sử dụng 'stars'
        return Response({'average_rating': average}, status=status.HTTP_200_OK)


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
    parser_classes = [parsers.MultiPartParser, ]

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

    @action(methods=['post'], detail=True)
    def block_user(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': 'User blocked successfully'})


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


class ReportViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.ListAPIView):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer
    permission_classes = [permissions.IsAuthenticated]  # Ensure the user is authenticated

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(reporter=self.request.user)
        else:
            raise serializers.ValidationError("You must be logged in to report a user.")


class FollowViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.ListAPIView):
    queryset = Follow.objects.all()
    serializer_class = serializers.FollowSerializer
    permission_classes = [permissions.IsAuthenticated]


class ImageViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.ListAPIView):
    queryset = Image.objects.all()
    serializer_class = serializers.ImageSerializer

    def perform_create(self, serializer):
        # serializer.save(post=self.request.user.post_set.first())
        postId = self.request.data.get('post')  # Lấy postId từ yêu cầu POST
        post = get_object_or_404(Post, pk=postId)  # Lấy post từ cơ sở dữ liệu
        serializer.save(post=post)  # Gán post cho ảnh


class RatingViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.ListAPIView):
    queryset = Rating.objects.all()
    serializer_class = serializers.RatingSerializer

    def create(self, request, *args, **kwargs):
        rater = request.user  # Người dùng đang rating
        post_id = request.data.get('post')
        stars = request.data.get('stars')

        try:
            # Lấy thông tin về bài đăng được rating
            post = Post.objects.get(pk=post_id)

            # Xác định các nhóm được phép rating bài đăng
            allowed_groups = Group.objects.filter(post=post)

            # Kiểm tra xem người dùng có thuộc bất kỳ nhóm nào được phép rating không
            is_allowed_to_rate = any(group.members.filter(id=rater.id).exists() for group in allowed_groups)

            # Nếu người dùng không thuộc bất kỳ nhóm nào được phép rating, trả về lỗi
            if not is_allowed_to_rate:
                return Response({'error': 'You are not allowed to rate this post'}, status=status.HTTP_403_FORBIDDEN)

            # Tạo rating cho bài đăng
            Rating.objects.create(rater=rater, post=post, stars=stars)

            return Response({'message': 'Rating created successfully'}, status=status.HTTP_201_CREATED)

        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)