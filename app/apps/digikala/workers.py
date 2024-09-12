from apps.accounts.models import Profile


async def check_new_notifications():
    await Profile.find().to_list()
