
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from smart_agri.core.models import Farm, Location, Asset, Crop, FarmCrop, Task, Supervisor, Item
class Command(BaseCommand):
    help = "Import JSON fixtures from a folder (farms, locations, assets, crops, farm_crops, tasks, supervisors)."
    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(Path(__file__).resolve().parents[4] / "fixtures"))
    def handle(self, *args, **opts):
        d = Path(opts["dir"]); self.stdout.write(self.style.WARNING(f"Using fixtures from: {d}"))
        def load(name):
            p = d / f"{name}.json"
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        farms = load("farms"); slug_to_farm = {}
        for f in farms:
            obj, _ = Farm.objects.get_or_create(slug=f["slug"], defaults={"name":f["name"], "region":f.get("region","")})
            slug_to_farm[f["slug"]] = obj
        for r in load("locations"):
            farm = slug_to_farm[r["farm_slug"]]
            Location.objects.get_or_create(farm=farm, name=r["name"], defaults={"type":r.get("type","Field"), "code":r.get("code","")})
        for r in load("assets"):
            farm = slug_to_farm[r["farm_slug"]]
            Asset.objects.get_or_create(farm=farm, category=r.get("category","Well"), name=r["name"])
        name_mode_to_crop = {}
        for c in load("crops"):
            from smart_agri.core.models import Crop as CropModel
            obj, _ = CropModel.objects.get_or_create(name=c["name"], mode=c.get("mode","Open"))
            name_mode_to_crop[(c["name"], c.get("mode","Open"))] = obj
        for r in load("farm_crops"):
            from smart_agri.core.models import FarmCrop as FC
            farm = slug_to_farm[r["farm_slug"]]; crop = name_mode_to_crop[(r["crop"], r.get("mode","Open"))]
            FC.objects.get_or_create(farm=farm, crop=crop)
        for t in load("tasks"):
            crop = name_mode_to_crop[(t["crop"], t.get("mode","Open"))]
            Task.objects.get_or_create(crop=crop, stage=t["stage"], name=t["name"])
        for s in load("supervisors"):
            farm = slug_to_farm[s["farm_slug"]]
            Supervisor.objects.get_or_create(farm=farm, code=s["code"], defaults={"name": s["name"]})
        for it in load("items"):
            Item.objects.get_or_create(name=it['name'], group=it['group'], defaults={'uom': it['uom']})
        self.stdout.write(self.style.SUCCESS("Fixtures imported successfully."))
