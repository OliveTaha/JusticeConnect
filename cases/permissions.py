from accounts.models import Account


def is_case_staff(user, case):
    """Court staff of the court that owns this case."""
    return user.role == Account.COURT_STAFF and hasattr(user, "staff") and user.staff.court_id == case.court_id


def is_case_client(user, case):
    return user.role == Account.CLIENT and case.client.account_id == user.id


def is_case_lawyer(user, case):
    return user.role == Account.LAWYER and hasattr(user, "lawyer") and case.assigned_lawyer_id == user.lawyer.id


def can_view(user, case):
    if user.is_superuser or is_case_staff(user, case) or is_case_client(user, case) or is_case_lawyer(user, case):
        return True
    if user.role == Account.LAWYER and hasattr(user, "lawyer"):
        # a verified lawyer can read open cases, and any lawyer can read a case he asked for
        return (user.is_verified and case.status == "open") or case.requests.filter(lawyer=user.lawyer).exists()
    return False


def can_add_document(user, case):
    # court staff, the client and the assigned lawyer can upload
    return is_case_staff(user, case) or is_case_client(user, case) or is_case_lawyer(user, case)
