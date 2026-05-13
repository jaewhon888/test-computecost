from .models import Owner


def owner_logo(request):
    """เพิ่ม owner logo ให้ทุก template ผ่าน base.html"""
    owners = Owner.objects.exclude(logo='').order_by('name')
    return {
        'owner_logos': list(owners),
    }
