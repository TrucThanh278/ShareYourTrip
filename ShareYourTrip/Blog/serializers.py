from rest_framework import serializers
from Blog.models import Post, Rating, Report, Comment, Hashtag, User, Image, Group, Follow
from django.db.models import Avg
class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ['id', 'hashtag']

class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.image:
            rep['image'] = instance.image.url

        return rep

class PostUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'avatar']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.avatar:
            rep['avatar'] = instance.avatar.url

        return rep

class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'rater', 'post', 'stars']

class PostSerializer(serializers.ModelSerializer):
    hashtags = serializers.PrimaryKeyRelatedField(queryset=Hashtag.objects.all(), many=True)
    user = PostUserSerializer(read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    class Meta:
        model = Post
        fields = ['id', 'title', 'starting_point', 'end_point', 'hashtags', 'user', 'start_time', 'end_time', 'cost',
                  'description', "ratings"]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.user.avatar:
            rep['user']['avatar'] = instance.user.avatar.url

        return rep

    def create(self, validated_data):
        hashtags_data = validated_data.pop('hashtags')
        post = Post.objects.create(**validated_data)
        post.hashtags.set(hashtags_data)
        return post

class PostDetailSerializer(serializers.ModelSerializer):
    hashtags = HashtagSerializer(many=True, read_only=True)
    user = PostUserSerializer(read_only=True)
    class Meta:
        model = Post
        fields = '__all__'

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.user.avatar:
            rep['user']['avatar'] = instance.user.avatar.url

        return rep

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    reported_user = serializers.SerializerMethodField()
    reporter = serializers.SerializerMethodField()
    following = serializers.SerializerMethodField()
    followers = serializers.SerializerMethodField()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password is not None:
            user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'gender', 'avatar',
                  'address', 'date_of_birth', 'reported_user', 'reporter', 'following', 'followers']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def get_reported_user(self, obj):
        return obj.reported_user.count()

    def get_reporter(self, obj):
        return obj.reporter.count()

    def get_following(self, obj):
        return obj.following.count()

    def get_followers(self, obj):
        return obj.followers.count()

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.avatar:
            rep['avatar'] = instance.avatar.url
        return rep

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'

class ReportSerializer(serializers.ModelSerializer):
    reported_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    reporter = serializers.ReadOnlyField(source='reporter.username')

    class Meta:
        model = Report
        fields = ['id', 'created_date', 'content', 'reported_user', 'reporter']

    def validate(self, data):
        if self.context['request'].user == data['reported_user']:
            raise serializers.ValidationError("You cannot report yourself.")
        return data

class FollowSerializer(serializers.ModelSerializer):
    follower_id = serializers.PrimaryKeyRelatedField(source='follower', queryset=User.objects.all())
    following_id = serializers.PrimaryKeyRelatedField(source='following', queryset=User.objects.all())

    class Meta:
        model = Follow
        fields = ['id', 'follower_id', 'following_id', 'created_date']


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ['id', 'image', 'name', 'post']
        read_only_fields = ['id', 'post']



# Sử dụng lại chính serializers của cha để serialize cho các comment con
# self.parent là serializers của lớp RecursiveField -> CommentSerializer sử dụng nó thì đó là CommentSerializers
# context: là 1 dict chứa các thông tin cần thiết trong qtrinh serialization: request, view, parameter,... -> đảm bảo dữ liệu cần thiết được truyền đúng cách từ serializer cha xuống con

class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data
    

class CommentSerializer(serializers.ModelSerializer):
    replies = RecursiveField(many=True, read_only=True)
    user = PostUserSerializer(read_only=True)
    class Meta:
        model = Comment
        fields = ['id', 'content', 'confirmed', 'created_date', 'updated_date', 'user', 'replies']

