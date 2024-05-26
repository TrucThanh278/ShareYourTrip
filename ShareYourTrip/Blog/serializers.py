from rest_framework import serializers
from Blog.models import Post, Rating, Report, Comment, Hashtag, User

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

class UserSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        data = validated_data.copy()
        u = User(**data)
        u.set_password(u.password)
        u.save()
        return u

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name', 'email', 'phone_number', 'avatar']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.avatar:
            rep['avatar'] = instance.avatar.url

        return rep
   

# Sử dụng lại chính serializers của cha để serialize cho các comment con
# self.parent là serializers của lớp RecursiveField -> CommentSerializer sử dụng nó thì đó là CommentSerializers
# context: là 1 dict chứa các thông tin cần thiết trong qtrinh serialization: request, view, parameter,... -> đảm bảo dữ liệu cần thiết được truyền đúng cách từ serializer cha xuống con

class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data
    

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'