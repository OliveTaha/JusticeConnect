from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.utils import paginate

from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related("case")
    only_unread = request.GET.get("show") == "unread"
    if only_unread:
        notifications = notifications.filter(is_read=False)
    context = {"page": paginate(request, notifications, 12), "only_unread": only_unread}
    return render(request, "notifications/list.html", context)


@login_required
def notification_open(request, pk):
    # mark as read, then go to the case the notification is about
    notification = get_object_or_404(Notification, pk=pk, account=request.user)
    notification.mark_as_read()
    if notification.case_id:
        return redirect("cases:detail", pk=notification.case_id)
    return redirect("notifications:list")


@login_required
def mark_all_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")


@login_required
def notification_delete(request, pk):
    notification = get_object_or_404(Notification, pk=pk, account=request.user)
    if request.method == "POST":
        notification.delete()
    return redirect("notifications:list")


@login_required
def clear_read(request):
    if request.method == "POST":
        request.user.notifications.filter(is_read=True).delete()
        messages.success(request, "Read notifications removed.")
    return redirect("notifications:list")
