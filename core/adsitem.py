from .models import DisplayAds,Item

def suggestItem(request):
    if not request.user.is_anonymous:
        Target = DisplayAds.objects.filter(
            user = request.user
        )
    else:
        Target=[]
    if (len(Target)>0):
        return {'advert': Target[0]}
    else:
        return {'advert': Target}