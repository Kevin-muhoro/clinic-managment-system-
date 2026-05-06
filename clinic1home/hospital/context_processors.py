def user_groups(request):
    if request.user.is_authenticated:
        return {
            'user_groups': [group.name for group in request.user.groups.all()]
        }
    return {'user_groups': []}