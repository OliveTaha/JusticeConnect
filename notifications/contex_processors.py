def unread_count(request):
    # used by the navbar to show the number of unread notifications
    if request.user.is_authenticated:
        return {"unread_count": request.user.notifications.filter(is_read=False).count()}
    return {}
