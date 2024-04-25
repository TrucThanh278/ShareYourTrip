from django.contrib import admin
from Blog.models import Post, Hashtag, Comment, Report, Group, Image, User, Rating
from django.utils.html import mark_safe
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
import cloudinary


class PostForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget)
    class Meta:
        model: Post
        fields: '__all__'


class PostAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Post._meta.fields]
    form = PostForm

    def my_image(self, Post):
        if Post.image:
            if type(Post.image) is cloudinary.CloudinaryResource:
                return mark_safe(f"<img width='300' src='{Post.image.url}' />")
            return mark_safe(f"<img width='300' src='/static/{Post.image.name}' />")


admin.site.register(Post, PostAdmin)
admin.site.register(Comment)
admin.site.register(Hashtag)
admin.site.register(Rating)
admin.site.register(Report)
admin.site.register(Image)
admin.site.register(User)
admin.site.register(Group)