
def user_ding_attributes(user, service):
    """Return all available user name related fields and methods."""
    attributes = {}
    attributes['ding_user_id'] = user.dinguser.user_id
    attributes['mobile'] = user.dinguser.mobile or user.profile.mobile
    return attributes