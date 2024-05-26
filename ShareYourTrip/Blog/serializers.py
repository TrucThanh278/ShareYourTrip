from rest_framework import serializers
from Blog.models import Post, Rating, Report, Comment, Hashtag, User, Follow

CLOUDINARY_DOMAIN = 'https://res.cloudinary.com/dsvodlq5d/'
from django.db.models import Avg


class UserSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'fullname', 'date_of_birth', 'gender', 'email', 'phone_number', 'address', 'avatar',
                  'username', 'password', 'followers_count', 'following_count', 'average_rating']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'id': {
                'read_only': True
            }
        }

    # def create(self, validated_data):
    #     user = User(**validated_data)
    #     user.set_password(validated_data['password'])
    #     user.save()
    #     return user
    def create(self, validated_data):
        user = User(**validated_data)

        user.set_password(validated_data['password'])

        if validated_data.get('role') == 'admin':
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False

        user.save()
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
            validated_data.pop('password')

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if 'role' in validated_data and validated_data['role'] != instance.role:
            if validated_data['role'] == 'admin':
                instance.is_superuser = True
                instance.is_staff = True
            else:
                instance.is_superuser = False
                instance.is_staff = False

        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if 'avatar' in data and data['avatar']:
            data['avatar'] = f"{CLOUDINARY_DOMAIN}{data['avatar']}"

        return data

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_average_rating(self, obj):
        ratings = obj.received_ratings.all()
        if ratings.exists():
            average = ratings.aggregate(Avg('stars'))['stars__avg']
            return round(average, 2)
        return 0

class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ['id', 'hashtag']


class PostSerializer(serializers.ModelSerializer):
    hashtags = HashtagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = ['title', 'starting_point', 'end_point', 'hashtags']


class PostUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class PostDetailSerializer(serializers.ModelSerializer):
    hashtags = HashtagSerializer(many=True, read_only=True)
    user = PostUserSerializer(read_only=True)

    class Meta:
        model = Post
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


class RatingSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Rating
        # fields = ['id', 'stars', 'created_date', 'updated_date', 'user']
        fields = '__all__'



class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.PrimaryKeyRelatedField(read_only=True)
    followed = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Follow
        fields = ['follower', 'followed']

