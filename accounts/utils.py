from django.core.paginator import Paginator


def paginate(request, queryset, per_page=10):
    """Returns one page of the queryset. page.query keeps the search filters in the page links."""
    page = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    page.query = params.urlencode()
    return page
