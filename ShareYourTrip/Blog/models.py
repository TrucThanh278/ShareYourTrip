from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from ckeditor.fields import RichTextField

class User(AbstractUser):
    GENDER_CHOICES = [
        ('men', 'Men'),
        ('women', 'Women'),
        ('others', 'Others')
    ]

    role_choices = [
        ('user', 'User'),
        ('admin', 'Admin')
    ]
    report_count = models.IntegerField(default=0)
    avatar = CloudinaryField('avatar', null=True, blank=True)
    phone_number = models.CharField(max_length=10, null=True, unique=True, blank=True)
    date_of_birth = models.DateField(null=True)
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(
        max_length=10,
        choices=role_choices,
        default='user',
        null=False
    )
    def increase_report_count(self):
        self.report_count += 1
        self.save()
    def __str__(self):
        return self.first_name + ' ' + self.last_name




class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True, null=False)
    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f'{self.follower.username} follows {self.following.username}'

class Interaction(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey('Post', on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Post(BaseModel):
    title = models.CharField(max_length=255, null=False)
    start_time = models.DateTimeField(null=False, blank=False)
    end_time = models.DateTimeField(null=False, blank=False)
    cost = models.FloatField(null=True, blank=True)
    starting_point = models.CharField(max_length=255, null=False, blank=False)
    end_point = models.CharField(max_length=255, null=False, blank=False)
    status = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)
    hashtags = models.ManyToManyField('Hashtag', blank=True)
    description = RichTextField()

    def __str__(self):
        return self.title


class Image(models.Model):
    image = CloudinaryField()
    post = models.ForeignKey(Post, related_name='images', on_delete=models.CASCADE)


class Hashtag(BaseModel):
    hashtag = models.CharField(max_length=255, blank=True, null=False, unique=True)

    def __str__(self):
        return self.hashtag


class Comment(Interaction):
    content = models.TextField(max_length=1000)
    confirmed = models.BooleanField(default=False)
    updated_date = models.DateTimeField(auto_now=True)
    parent_comment = models.ForeignKey('self', related_name='replies', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        ordering = ['-created_date', '-updated_date']
        get_latest_by = ['created_date']



    def __str__(self):
        return f'Comment by {self.user.username} on {self.post.title} with content: {self.content}'



class Rating(models.Model):
    rater = models.ForeignKey(User, related_name='given_ratings', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='ratings', on_delete=models.CASCADE)
    stars = models.IntegerField(choices=[(i, i) for i in range(1, 6)], null=True, default=1)

    class Meta:
        unique_together = ('rater', 'post')

    def __str__(self):
        return f'Rating: {self.stars} stars by {self.rater.username} for Post ID: {self.post.id}'


class Like(Interaction):
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f'Like by {self.user.username} on {self.post.title}'


class Group(BaseModel):
    creator = models.ForeignKey(User, related_name='created_groups', on_delete=models.CASCADE)
    post = models.OneToOneField(Post, on_delete=models.CASCADE, primary_key=True)
    members = models.ManyToManyField(User, related_name='group_members')  # Thay đổi related_name thành 'group_members'

    def __str__(self):
        return f'Group for post: {self.post.title}'

class Report(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, null=False)
    content = models.TextField(max_length=1000)
    reported_user = models.ForeignKey(User, related_name='reported_user', on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, related_name='reporter', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('reporter', 'reported_user')
