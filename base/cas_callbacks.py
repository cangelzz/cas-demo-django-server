
def user_profile_attributes(user, service):
    """Return all available user name related fields and methods."""
    attributes = {}
    attributes['username'] = user.get_username()
    attributes['fullname'] = user.profile.fullname()
    attributes['name'] = user.profile.full_name
    return attributes