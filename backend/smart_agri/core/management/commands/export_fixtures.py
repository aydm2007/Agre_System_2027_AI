
from django.core.management.base import BaseCommand
from smart_agri.core.models import Farm, Location, Asset, Crop, FarmCrop, Task, Supervisor
import json
from pathlib import Path
class Command(BaseCommand):
    help = "Export current data to JSON files in the given directory."
    def add_arguments(self, parser):
        parser.add_argument("--dir", default="exported_fixtures")
    def handle(self, *args, **opts):
        out = Path(opts["dir"]); out.mkdir(parents=True, exist_ok=True)
        def dump(name, data):
            (out/f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        farms = [{"name":f.name,"slug":f.slug,"region":f.region} for f in Farm.objects.alive()]
        dump("farms", farms)
        locations = [{"farm_slug":l.farm.slug,"name":l.name,"type":l.type,"code":l.code or ""} for l in Location.objects.alive()]
        dump("locations", locations)
        assets = [{"farm_slug":a.farm.slug,"name":a.name,"category":a.category} for a in Asset.objects.alive()]
        dump("assets", assets)
        crops = [{"name":c.name,"mode":c.mode} for c in Crop.objects.alive()]
        dump("crops", crops)
        fcs = [{"farm_slug":fc.farm.slug,"crop":fc.crop.name,"mode":fc.crop.mode} for fc in FarmCrop.objects.alive()]
        dump("farm_crops", fcs)
        tasks = [{"crop":t.crop.name,"mode":t.crop.mode,"stage":t.stage,"name":t.name} for t in Task.objects.alive()]
        dump("tasks", tasks)
        supervisors = [{"farm_slug":s.farm.slug,"name":s.name,"code":s.code} for s in Supervisor.objects.alive()]
        dump("supervisors", supervisors)
        self.stdout.write(self.style.SUCCESS(f"Exported fixtures to {out.resolve()}"))
