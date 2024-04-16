from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField


class User(AbstractUser):
    GENDER = [
        ('men', 'MEN'),
        ('women', 'Women'),
        ('others', 'Others')
    ]
    report_count = models.IntegerField(default=0)
    avatar = CloudinaryField(null=True)
    phone_number = models.CharField(max_length=9, null=False, unique=True, blank=False)
    gender = models.CharField(max_length=6, choices=GENDER)
    address = models.CharField(max_length=100)

    def increase_report_count(self):
        self.report_count += 1

    def __str__(self):
        return self.last_name + " " + self.first_name


class BaseModel(models.Model):

    class Meta:
        abstract = True

    created_date = models.DateTimeField(auto_now_add=True, null=False)
    updated_date = models.DateTimeField(auto_now=True, null=False)
    description = models.TextField(max_length=255, null=True, blank=True)


class Post(BaseModel):
    title = models.TextField(max_length=255, null=False)
    start_time = models.DateTimeField(null=False, blank=False)
    end_time = models.DateTimeField(null=False, blank=False)
    cost = models.FloatField(null=True)
    starting_point = models.TextField(max_length=255, null=False, blank=False)
    end_point = models.TextField(max_length=255, null=False, blank=False)
    status = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    images = models.ManyToManyField('Image')
    hashtags = models.ManyToManyField('Hashtag')

    def __str__(self):
        return self.title


class Image(models.Model):
    image = CloudinaryField()


class Hashtag(models.Model):
    hashtag = models.CharField(max_length=255, blank=True, null=False, unique=True)

    def __str__(self):
        return self.hashtag


class Interaction(models.Model):

    class Meta:
        abstract = True

    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class Comment(Interaction):
    content = models.TextField(max_length=255)
    confirmed = models.BooleanField(default=None)


class Rating(models.Model):
    stars = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user',)


class Group(models.Model):
    creator = models.ForeignKey(User, related_name='created_groups', on_delete=models.CASCADE)
    post = models.OneToOneField(Post, on_delete=models.CASCADE, primary_key=True)
    created_date = models.DateTimeField(auto_now_add=True, null=False)
    members = models.ManyToManyField(User, related_name='members')

    def __str__(self):
        return "Group " + self.post.name


class Report(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, null=False)
    content = models.TextField(max_length=255, null=False)
    reported_user = models.ForeignKey(User, related_name='reported_user', on_delete=models.CASCADE)
    reporting_user = models.ForeignKey(User, related_name='reported_made', on_delete=models.CASCADE)