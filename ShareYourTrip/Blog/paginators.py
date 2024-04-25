from rest_framework import pagination

class CommentPaginator(pagination.PageNumberPagination):
    page_size = 2

class ItemPaginator(pagination.PageNumberPagination):
    page_size = 2