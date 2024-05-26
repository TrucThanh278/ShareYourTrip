from rest_framework import permissions

from rest_framework.permissions import BasePermission


class OwnerAuthenticated(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, obj):
        return super().has_permission(request, view) and request.user == obj.user


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='admin').exists()

    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.groups.filter(name='admin').exists()


class IsUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='user').exists()

class CommentOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, comment):
        return super().has_permission(request, view) and request.user == comment.user
    
class PostOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, post):
        return object.post.user == request.user