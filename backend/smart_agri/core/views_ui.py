from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import Asset, Farm, Crop, FarmCrop, Task, Location

@login_required
def farms_list(request):
    q = request.GET.get("q","").strip()
    qs = Farm.objects.alive().filter(name__icontains=q) if q else Farm.objects.alive()
    if request.htmx:
        return render(request, "partials/farms_table_rows.html", {"farms": qs})
    return render(request, "farms_list.html", {"farms": qs, "q": q})

@login_required
def daily_log_new(request):
    farms = Farm.objects.alive().order_by("name")
    return render(request, "daily_log_new.html", {"farms": farms})

@login_required
def options_crops_for_farm(request, farm_id:int):
    crop_ids = FarmCrop.objects.alive().filter(farm_id=farm_id).values_list("crop_id", flat=True)
    crops = Crop.objects.alive().filter(id__in=crop_ids)
    return render(request, "partials/options_crops.html", {"crops": crops})

@login_required
def options_tasks_for_crop(request, crop_id:int):
    tasks = Task.objects.alive().filter(crop_id=crop_id).order_by("stage","name")
    return render(request, "partials/options_tasks.html", {"tasks": tasks})

@login_required
def options_locations_for_farm(request, farm_id:int):
    locs = Location.objects.alive().filter(farm_id=farm_id).order_by("name")
    return render(request, "partials/options_locations.html", {"locations": locs})

@login_required
def options_assets_for_farm(request, farm_id:int):
    assets = Asset.objects.alive().filter(farm_id=farm_id).order_by("name")
    return render(request, "partials/options_assets.html", {"assets": assets})

@login_required
def audit_list(request):
    from .models import AuditLog
    from django.core.paginator import Paginator

    page = int(request.GET.get("page", "1"))
    action = request.GET.get("action", "").strip()
    user = request.GET.get("user", "").strip()
    model = request.GET.get("model", "").strip()

    qs = AuditLog.objects.all().order_by("-timestamp")
    if action:
        qs = qs.filter(action__icontains=action)
    if user:
        qs = qs.filter(user__username__icontains=user)
    if model:
        qs = qs.filter(model__icontains=model)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page)

    context = {"page": page_obj, "action": action, "user": user, "model": model}
    if request.htmx:
        return render(request, "partials/audit_rows.html", context)
    return render(request, "audit_list.html", context)

@login_required
def crop_tasks(request):
    q = request.GET.get("q","").strip()
    crops = Crop.objects.alive().order_by("name","mode")
    tasks = Task.objects.alive()
    if q:
        tasks = tasks.filter(Q(name__icontains=q) | Q(stage__icontains=q) | Q(crop__name__icontains=q))
    if request.htmx and request.method == "POST":
        crop_id = request.POST.get("crop_id")
        stage = request.POST.get("stage")
        name = request.POST.get("name")
        if crop_id and stage and name:
            crop = Crop.objects.get(id=crop_id)
            Task.objects.create(crop=crop, stage=stage, name=name)
    if request.htmx:
        return render(request, "partials/crop_tasks_rows.html", {"tasks": tasks.select_related("crop")})
    return render(request, "crop_tasks.html", {"crops": crops, "tasks": tasks.select_related("crop"), "q": q})
