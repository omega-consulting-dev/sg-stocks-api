from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Pagination personnalisée permettant au client de spécifier la taille de page.
    Par défaut: 20 résultats
    Maximum: 10000 résultats
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 10000
