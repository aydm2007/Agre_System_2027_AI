from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from smart_agri.accounts.models import FarmMembership
from smart_agri.core.models import (
    Activity,
    ActivityLocation,
    Crop,
    CropProduct,
    CropVariety,
    DailyLog,
    Farm,
    Item,
    Location,
    Task,
    TreeLossReason,
    TreeProductivityStatus,
    TreeServiceCoverage,
    TreeStockEvent,
)
from smart_agri.core.models.inventory import BiologicalAssetCohort
from smart_agri.core.services import TreeInventoryService


class TreeInventoryServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("service-user")
        self.farm = Farm.objects.create(name="Test Farm", slug="test-farm", region="A")
        self.location = Location.objects.create(farm=self.farm, name="Orchard 1", type="Orchard")
        self.crop = Crop.objects.create(name="Palm", mode="Open", is_perennial=True)
        self.variety = CropVariety.objects.create(crop=self.crop, name="Ajwa")
        self.daily_log = DailyLog.objects.create(farm=self.farm, log_date=date(2024, 1, 1))
        self.tree_task = Task.objects.create(
            crop=self.crop,
            stage="Maintenance",
            name="Tree care",
            requires_tree_count=True,
            is_perennial_procedure=True,
        )
        self.harvest_task = Task.objects.create(
            crop=self.crop,
            stage="Harvest",
            name="Fruit harvest",
            requires_tree_count=True,
            is_perennial_procedure=True,
            is_harvest_task=True,
        )
        harvest_item = Item.objects.create(name="Premium Dates", group="Harvested Product", uom="kg")
        self.crop_product = CropProduct.objects.create(
            crop=self.crop,
            name="Premium Dates",
            pack_size=1.0,
            pack_uom='kg'
        )
        self.loss_reason = TreeLossReason.objects.create(code="storm", name_en="Storm", name_ar="عاصفة")
        TreeProductivityStatus.objects.create(code="juvenile", name_en="Juvenile", name_ar="صغير")

        self.service = TreeInventoryService()

    def _make_activity(self, **overrides):
        defaults = {
            "log": self.daily_log,
            "crop": self.crop,
            "task": overrides.get("task", self.tree_task),
            "variety": overrides.get("variety", self.variety),
            "tree_count_delta": overrides.get("tree_count_delta", 0),
            "tree_loss_reason": overrides.get("tree_loss_reason"),
            "activity_tree_count": overrides.get("activity_tree_count"),
            "harvest_quantity": overrides.get("harvest_quantity"),
            "water_volume": overrides.get("water_volume"),
            "water_uom": overrides.get("water_uom"),
            "fertilizer_quantity": overrides.get("fertilizer_quantity"),
            "fertilizer_uom": overrides.get("fertilizer_uom"),
            "product": overrides.get("product", self.crop_product),
        }
        activity = Activity.objects.create(**defaults)
        location = overrides.get("location", self.location)
        if location:
            ActivityLocation.objects.create(activity=activity, location=location)
        return activity

    def test_planting_creates_stock_and_event(self):
        activity = self._make_activity(tree_count_delta=40)

        result = self.service.reconcile_activity(activity=activity, user=self.user)

        self.assertIsNotNone(result)
        stock = result.stock
        event = result.event
        stock.refresh_from_db()

        self.assertEqual(stock.current_tree_count, 40)
        self.assertEqual(event.event_type, TreeStockEvent.PLANTING)
        self.assertEqual(event.tree_count_delta, 40)
        self.assertEqual(event.resulting_tree_count, 40)
        self.assertEqual(event.location_tree_stock, stock)
        self.assertEqual(stock.planting_date, self.daily_log.log_date)
        self.assertEqual(event.planting_date, stock.planting_date)

    def test_loss_event_reduces_balance_and_links_reason(self):
        initial_activity = self._make_activity(tree_count_delta=60)
        self.service.reconcile_activity(activity=initial_activity, user=self.user)
        loss_activity = self._make_activity(tree_count_delta=-25, tree_loss_reason=self.loss_reason)

        result = self.service.reconcile_activity(activity=loss_activity, user=self.user)
        stock = result.stock
        event = result.event

        self.assertEqual(event.event_type, TreeStockEvent.LOSS)
        self.assertEqual(event.tree_count_delta, -25)
        self.assertEqual(event.loss_reason, self.loss_reason)
        self.assertEqual(event.resulting_tree_count, stock.current_tree_count)
        self.assertEqual(stock.current_tree_count, 35)

    def test_adjustment_event_when_delta_is_zero(self):
        initial_activity = self._make_activity(tree_count_delta=50)
        self.service.reconcile_activity(activity=initial_activity, user=self.user)
        adjustment_activity = self._make_activity(tree_count_delta=0, activity_tree_count=45)

        result = self.service.reconcile_activity(activity=adjustment_activity, user=self.user)
        stock = result.stock
        event = result.event

        self.assertEqual(event.event_type, TreeStockEvent.ADJUSTMENT)
        self.assertEqual(event.tree_count_delta, 0)
        self.assertEqual(event.resulting_tree_count, stock.current_tree_count)
        self.assertEqual(stock.current_tree_count, 50)

    def test_harvest_event_records_quantities_without_affecting_balance(self):
        initial_activity = self._make_activity(tree_count_delta=80)
        self.service.reconcile_activity(activity=initial_activity, user=self.user)
        harvest_activity = self._make_activity(
            task=self.harvest_task,
            tree_count_delta=0,
            harvest_quantity=Decimal("125.5"),
            water_volume=Decimal("10.25"),
            water_uom="m3",
        )

        result = self.service.reconcile_activity(activity=harvest_activity, user=self.user)
        stock = result.stock
        event = result.event

        self.assertEqual(event.event_type, TreeStockEvent.HARVEST)
        self.assertEqual(event.tree_count_delta, 0)
        self.assertEqual(event.resulting_tree_count, stock.current_tree_count)
        self.assertEqual(event.harvest_quantity, Decimal("125.5"))
        self.assertEqual(event.harvest_uom, "kg")
        self.assertEqual(event.water_volume, Decimal("10.25"))
        self.assertEqual(stock.current_tree_count, 80)


class TreeInventoryAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("api-user", password="pass")
        self.other_user = User.objects.create_user("no-access", password="pass")

        self.farm1 = Farm.objects.create(name="Farm One", slug="farm-one", region="North")
        self.farm2 = Farm.objects.create(name="Farm Two", slug="farm-two", region="East")
        FarmMembership.objects.create(user=self.user, farm=self.farm1, role="مدير المزرعة")

        self.location1 = Location.objects.create(farm=self.farm1, name="Orchard East", type="Orchard")
        self.location2 = Location.objects.create(farm=self.farm1, name="Orchard West", type="Orchard")
        self.location3 = Location.objects.create(farm=self.farm2, name="Remote Orchard", type="Orchard")

        self.crop = Crop.objects.create(name="Date Palm", mode="Open", is_perennial=True)
        self.variety1 = CropVariety.objects.create(crop=self.crop, name="Barhi")
        self.variety2 = CropVariety.objects.create(crop=self.crop, name="Medjool")
        self.variety3 = CropVariety.objects.create(crop=self.crop, name="Khalas")
        self.variety4 = CropVariety.objects.create(crop=self.crop, name="Sudani")

        self.task = Task.objects.create(
            crop=self.crop,
            stage="Maintenance",
            name="Tree pruning",
            requires_tree_count=True,
            is_perennial_procedure=True,
        )
        self.harvest_task = Task.objects.create(
            crop=self.crop,
            stage="Harvest",
            name="Palm harvest",
            requires_tree_count=True,
            is_perennial_procedure=True,
            is_harvest_task=True,
        )
        api_harvest_item = Item.objects.create(name="API Dates", group="Harvested Product", uom="kg")
        self.crop_product1 = CropProduct.objects.create(
            crop=self.crop,
            name="API Dates",
            pack_size=1.0,
            pack_uom='kg'
        )
        self.loss_reason = TreeLossReason.objects.create(code="storm", name_en="Storm", name_ar="عاصفة")
        self.status_juvenile = TreeProductivityStatus.objects.create(
            code="juvenile", name_en="Juvenile", name_ar="صغير"
        )
        self.status_mature = TreeProductivityStatus.objects.create(
            code="productive", name_en="Productive", name_ar="منتج"
        )

        self.log1 = DailyLog.objects.create(farm=self.farm1, log_date=date(2024, 1, 1))
        self.log2 = DailyLog.objects.create(farm=self.farm1, log_date=date(2024, 2, 1))
        self.log3 = DailyLog.objects.create(farm=self.farm2, log_date=date(2024, 3, 1))

        self.service = TreeInventoryService()
        self.client.force_authenticate(self.user)

        self._seed_tree_data()

    def _activity(self, *, log, location, variety, task=None, **overrides):
        payload = {
            "log": log,
            "crop": self.crop,
            "task": task or self.task,
            "variety": variety,
            "tree_count_delta": overrides.get("tree_count_delta", 0),
            "tree_loss_reason": overrides.get("tree_loss_reason"),
            "harvest_quantity": overrides.get("harvest_quantity"),
            "water_volume": overrides.get("water_volume"),
            "fertilizer_quantity": overrides.get("fertilizer_quantity"),
            "water_uom": overrides.get("water_uom"),
            "fertilizer_uom": overrides.get("fertilizer_uom"),
            "product": overrides.get("product", self.crop_product1),
        }
        activity = Activity.objects.create(**payload)
        ActivityLocation.objects.create(activity=activity, location=location)
        return activity

    def _seed_tree_data(self):
        # Farm 1, location 1: planting then loss
        plant1 = self._activity(log=self.log1, location=self.location1, variety=self.variety1, tree_count_delta=80)
        result1 = self.service.reconcile_activity(activity=plant1, user=self.user)
        self.stock1 = result1.stock
        loss_activity = self._activity(
            log=self.log2,
            location=self.location1,
            variety=self.variety1,
            tree_count_delta=-15,
            tree_loss_reason=self.loss_reason,
        )
        self.service.reconcile_activity(activity=loss_activity, user=self.user)

        service_activity_day1 = self._activity(
            log=self.log1,
            location=self.location1,
            variety=self.variety1,
            tree_count_delta=0,
            activity_tree_count=30,
        )
        TreeServiceCoverage.objects.create(
            activity=service_activity_day1,
            location=self.location1,
            crop_variety=self.variety1,
            service_count=30,
            service_type=TreeServiceCoverage.GENERAL,
            total_before=80,
            recorded_by=self.user,
        )
        service_activity_day2 = self._activity(
            log=self.log2,
            location=self.location1,
            variety=self.variety1,
            tree_count_delta=0,
            activity_tree_count=15,
        )
        TreeServiceCoverage.objects.create(
            activity=service_activity_day2,
            location=self.location1,
            crop_variety=self.variety1,
            service_count=15,
            service_type=TreeServiceCoverage.IRRIGATION,
            total_before=65,
            recorded_by=self.user,
        )

        # Farm 1, location 2: planting then harvest
        plant2 = self._activity(log=self.log1, location=self.location2, variety=self.variety2, tree_count_delta=50)
        result2 = self.service.reconcile_activity(activity=plant2, user=self.user)
        self.stock2 = result2.stock
        self.stock2.productivity_status = self.status_mature
        self.stock2.save(update_fields=["productivity_status"])
        harvest = self._activity(
            log=self.log2,
            location=self.location2,
            variety=self.variety2,
            task=self.harvest_task,
            tree_count_delta=0,
            harvest_quantity=Decimal("30.5"),
        )
        self.service.reconcile_activity(activity=harvest, user=self.user)

        BiologicalAssetCohort.objects.create(
            farm=self.farm1,
            location=self.location1,
            crop=self.crop,
            variety=self.variety1,
            batch_name="Loc1 productive",
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
            quantity=65,
            planted_date=date(2023, 3, 20),
        )
        BiologicalAssetCohort.objects.create(
            farm=self.farm1,
            location=self.location2,
            crop=self.crop,
            variety=self.variety2,
            batch_name="Loc2 productive",
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
            quantity=40,
            planted_date=date(2023, 3, 20),
        )
        BiologicalAssetCohort.objects.create(
            farm=self.farm1,
            location=self.location2,
            crop=self.crop,
            variety=self.variety2,
            batch_name="Loc2 excluded",
            status=BiologicalAssetCohort.STATUS_EXCLUDED,
            quantity=4,
            planted_date=date(2023, 3, 20),
        )
        BiologicalAssetCohort.objects.create(
            farm=self.farm1,
            location=self.location1,
            crop=self.crop,
            variety=self.variety4,
            batch_name="Loc1 cohort fallback",
            status=BiologicalAssetCohort.STATUS_PRODUCTIVE,
            quantity=232,
            planted_date=date(2023, 3, 20),
        )

        # Farm 2, location 3: planting only (should be hidden from user)
        plant3 = self._activity(log=self.log3, location=self.location3, variety=self.variety3, tree_count_delta=40)
        self.service.reconcile_activity(activity=plant3, user=self.user)

    def _extract_results(self, data):
        if isinstance(data, list):
            return data
        return data.get("results", [])

    def test_summary_list_filters_and_permissions(self):
        url = reverse("tree-inventory-summary-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._extract_results(response.data)
        self.assertEqual(len(results), 2)
        location_names = {item["location"]["name"] for item in results}
        self.assertIn(self.location1.name, location_names)
        self.assertIn(self.location2.name, location_names)
        self.assertNotIn(self.location3.name, location_names)

        filtered = self.client.get(url, {"location_id": self.location1.id})
        filtered_results = self._extract_results(filtered.data)
        self.assertEqual(len(filtered_results), 1)
        self.assertEqual(filtered_results[0]["location"]["name"], self.location1.name)

        status_filtered = self.client.get(url, {"status_code": self.status_mature.code})
        status_results = self._extract_results(status_filtered.data)
        self.assertTrue(all(entry["location"]["name"] == self.location2.name for entry in status_results))

        multi_location = self.client.get(
            url, {"location_id": f"{self.location1.id},{self.location2.id}"}
        )
        multi_results = self._extract_results(multi_location.data)
        self.assertEqual(len(multi_results), 2)

        noisy_location = self.client.get(url, {"location_id": f"{self.location1.id},bad"})
        noisy_results = self._extract_results(noisy_location.data)
        self.assertEqual(len(noisy_results), 1)
        self.assertEqual(noisy_results[0]["location"]["name"], self.location1.name)

        multi_variety = self.client.get(
            url, {"variety_id": f"{self.variety1.id},{self.variety2.id}"}
        )
        variety_results = self._extract_results(multi_variety.data)
        self.assertEqual(len(variety_results), 2)

        noisy_variety = self.client.get(url, {"variety_id": f"{self.variety1.id},oops"})
        noisy_variety_results = self._extract_results(noisy_variety.data)
        self.assertEqual(len(noisy_variety_results), 1)
        self.assertEqual(noisy_variety_results[0]["location"]["name"], self.location1.name)

    def test_summary_includes_service_stats_and_filters_by_service_range(self):
        url = reverse("tree-inventory-summary-list")
        response = self.client.get(
            url,
            {
                "location_id": self.location1.id,
                "service_start": "2024-01-01",
                "service_end": "2024-01-01",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._extract_results(response.data)
        self.assertEqual(len(results), 1)
        current_balance = results[0].get('current_tree_count') or 0
        stats = results[0].get("service_stats")
        self.assertIsNotNone(stats)
        period = stats.get('period') or {}
        lifetime = stats.get('lifetime') or {}
        latest = stats.get('latest_entry') or {}
        self.assertEqual(period.get('total_serviced'), 30)
        self.assertEqual(period.get('entries'), 1)
        self.assertEqual(period.get('breakdown', {}).get('general'), 30)
        self.assertEqual(period.get('breakdown', {}).get('irrigation'), 0)
        self.assertEqual(period.get('last_service_date'), '2024-01-01')
        if current_balance:
            self.assertAlmostEqual(float(period.get('coverage_ratio') or 0), float(30) / float(current_balance), places=4)
        self.assertEqual(lifetime.get('total_serviced'), 45)
        self.assertEqual(lifetime.get('breakdown', {}).get('general'), 30)
        self.assertEqual(lifetime.get('breakdown', {}).get('irrigation'), 15)
        self.assertEqual(lifetime.get('last_service_date'), '2024-02-01')
        if current_balance:
            self.assertAlmostEqual(float(lifetime.get('coverage_ratio') or 0), float(45) / float(current_balance), places=4)
        self.assertTrue(float(lifetime.get('coverage_ratio') or 0) >= float(period.get('coverage_ratio') or 0))
        self.assertEqual(latest.get('service_type'), TreeServiceCoverage.IRRIGATION)
        self.assertEqual(latest.get('service_count'), 15)
        self.assertEqual(latest.get('activity_date'), '2024-02-01')
        self.assertEqual(latest.get('recorded_by_name'), 'api-user')

    def test_location_summary_endpoint_returns_perennial_stocks(self):
        url = reverse("tree-inventory-summary-location-summary")
        response = self.client.get(url, {"location_id": self.location1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data
        self.assertEqual(payload["location"]["id"], self.location1.id)
        scope_values = {entry["value"] for entry in payload.get("service_scopes", [])}
        self.assertIn(TreeServiceCoverage.GENERAL, scope_values)
        self.assertIn(TreeServiceCoverage.IRRIGATION, scope_values)
        stocks = payload.get("stocks") or []
        self.assertTrue(stocks)
        stock_map = {item["crop_variety_id"]: item for item in stocks}
        self.assertIn(self.variety1.id, stock_map)
        service_info = stock_map[self.variety1.id].get("service") or {}
        lifetime = service_info.get("lifetime") or {}
        breakdown = lifetime.get("breakdown") or {}
        self.assertIn("general", breakdown)
        self.assertIn("cleaning", breakdown)
        latest = service_info.get("latest") or {}
        self.assertIn("service_scope", latest)

    def test_location_variety_summary_matches_stock_and_flags_reconciliation_gap(self):
        url = reverse("tree-inventory-summary-location-variety-summary")
        response = self.client.get(
            url,
            {
                "farm_id": self.farm1.id,
                "crop_id": self.crop.id,
                "location_ids": f"{self.location1.id},{self.location2.id}",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        variety_map = {entry["variety_id"]: entry for entry in results}

        self.assertIn(self.variety1.id, variety_map)
        self.assertIn(self.variety2.id, variety_map)

        loc1_summary = variety_map[self.variety1.id]
        self.assertEqual(loc1_summary["current_tree_count_total"], 65)
        self.assertEqual(loc1_summary["cohort_alive_total"], 65)
        self.assertEqual(loc1_summary["cohort_stock_delta"], 0)
        self.assertFalse(loc1_summary["has_reconciliation_gap"])

        loc2_summary = variety_map[self.variety2.id]
        self.assertEqual(loc2_summary["current_tree_count_total"], 50)
        self.assertEqual(loc2_summary["cohort_alive_total"], 40)
        self.assertEqual(loc2_summary["cohort_stock_delta"], -10)
        self.assertTrue(loc2_summary["has_reconciliation_gap"])
        self.assertEqual(
            loc2_summary["by_location"][str(self.location2.id)]["current_tree_count"],
            50,
        )
        self.assertEqual(
            loc2_summary["by_location"][str(self.location2.id)]["cohort_alive_total"],
            40,
        )

    def test_location_variety_summary_filters_out_non_selected_locations(self):
        url = reverse("tree-inventory-summary-location-variety-summary")
        response = self.client.get(
            url,
            {
                "farm_id": self.farm1.id,
                "crop_id": self.crop.id,
                "location_ids": str(self.location1.id),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        variety_ids = {entry["variety_id"] for entry in results}
        self.assertEqual(variety_ids, {self.variety1.id, self.variety4.id})

    def test_multi_location_service_rows_accept_cohort_fallback_when_stock_row_is_missing(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id],
            "variety_id": self.variety4.id,
            "activity_tree_count": 2,
            "tree_count_delta": 0,
            "service_counts_payload": [
                {
                    "location_id": self.location1.id,
                    "variety_id": self.variety4.id,
                    "service_count": 2,
                    "service_type": TreeServiceCoverage.GENERAL,
                }
            ],
        }

        response = self.client.post(
            url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="key-cohort-fallback",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_positive_tree_delta_allows_new_variety_location_service_row_without_prior_stock(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id],
            "variety_id": self.variety3.id,
            "activity_tree_count": 5,
            "tree_count_delta": 5,
            "service_counts_payload": [
                {
                    "location_id": self.location1.id,
                    "variety_id": self.variety3.id,
                    "service_count": 5,
                    "service_type": TreeServiceCoverage.GENERAL,
                }
            ],
        }

        response = self.client.post(
            url,
            payload,
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="key-positive-new-variety-location",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_activity_crud_synchronises_service_coverage_rows(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id],
            "variety_id": self.variety1.id,
            "activity_tree_count": 120,
            "tree_count_delta": 0,
            "service_counts_payload": [
                {
                    "location_id": self.location1.id,
                    "variety_id": self.variety1.id,
                    "service_count": 20,
                    "service_type": TreeServiceCoverage.GENERAL,
                    "distribution_mode": "equal",
                },
                {
                    "location_id": self.location1.id,
                    "variety_id": self.variety1.id,
                    "service_count": 15,
                    "service_type": TreeServiceCoverage.IRRIGATION,
                    "notes": "ري تكميلي",
                },
            ],
        }

        response = self.client.post(url, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="key-1")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity_id = response.data["id"]

        coverages = list(
            TreeServiceCoverage.objects.filter(
                activity_id=activity_id, deleted_at__isnull=True
            ).order_by("service_type")
        )
        self.assertEqual(len(coverages), 2)
        self.assertEqual(coverages[0].location_id, self.location1.id)
        self.assertEqual(coverages[0].crop_variety_id, self.variety1.id)
        self.assertEqual(coverages[0].service_type, TreeServiceCoverage.GENERAL)
        self.assertEqual(coverages[0].service_scope, TreeServiceCoverage.GENERAL)
        self.assertEqual(coverages[0].distribution_mode, TreeServiceCoverage.DISTRIBUTION_UNIFORM)
        self.assertEqual(coverages[0].service_count, 20)
        self.assertEqual(coverages[0].recorded_by_id, self.user.id)
        self.assertEqual(coverages[1].notes, "ري تكميلي")
        self.assertEqual(coverages[1].service_scope, TreeServiceCoverage.IRRIGATION)

        update_payload = {
            "service_counts_payload": [
                {
                    "location_id": self.location1.id,
                    "variety_id": self.variety1.id,
                    "service_count": 50,
                    "service_type": TreeServiceCoverage.FERTILIZATION,
                }
            ]
        }
        detail_url = reverse("activities-detail", args=[activity_id])
        update_response = self.client.patch(detail_url, update_payload, format="json", HTTP_X_IDEMPOTENCY_KEY="key-2")
        if update_response.status_code != status.HTTP_200_OK:
            print("UPDATE ERROR:", update_response.data)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        refreshed_coverages = list(
            TreeServiceCoverage.objects.filter(
                activity_id=activity_id, deleted_at__isnull=True
            ).order_by("service_type")
        )
        print("REFRESHED COVERAGES:", refreshed_coverages)
        self.assertTrue(
            any(
                entry.service_type == TreeServiceCoverage.FERTILIZATION
                and entry.service_count == 50
                for entry in refreshed_coverages
            ),
            refreshed_coverages,
        )
        self.assertFalse(
            any(entry.service_count in {20, 15} for entry in refreshed_coverages),
            refreshed_coverages,
        )
        for entry in refreshed_coverages:
            self.assertEqual(entry.location_id, self.location1.id)
            self.assertEqual(entry.crop_variety_id, self.variety1.id)
            self.assertEqual(entry.recorded_by_id, self.user.id)

    def test_multi_location_service_rows_require_explicit_row_location(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id, self.location2.id],
            "variety_id": self.variety1.id,
            "activity_tree_count": 10,
            "tree_count_delta": 0,
            "service_counts_payload": [
                {
                    "variety_id": self.variety1.id,
                    "service_count": 10,
                    "service_type": TreeServiceCoverage.GENERAL,
                }
            ],
        }

        response = self.client.post(url, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="key-row-location")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_counts", response.data.get("error", {}).get("details", {}))

    def test_multi_location_service_rows_reject_variety_outside_row_location(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id, self.location2.id],
            "variety_id": self.variety1.id,
            "activity_tree_count": 10,
            "tree_count_delta": 0,
            "service_counts_payload": [
                {
                    "location_id": self.location2.id,
                    "variety_id": self.variety1.id,
                    "service_count": 10,
                    "service_type": TreeServiceCoverage.GENERAL,
                }
            ],
        }

        response = self.client.post(url, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="key-variety-location")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("service_counts", response.data.get("error", {}).get("details", {}))

    def test_multi_location_service_rows_accept_row_specific_location_and_variety_pairs(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id, self.location2.id],
            "variety_id": self.variety1.id,
            "activity_tree_count": 20,
            "tree_count_delta": 0,
            "service_counts_payload": [
                {
                    "location_id": self.location1.id,
                    "variety_id": self.variety1.id,
                    "service_count": 10,
                    "service_type": TreeServiceCoverage.GENERAL,
                },
                {
                    "location_id": self.location2.id,
                    "variety_id": self.variety2.id,
                    "service_count": 10,
                    "service_type": TreeServiceCoverage.PRUNING,
                },
            ],
        }

        response = self.client.post(url, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="key-row-specific")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        coverages = list(
            TreeServiceCoverage.objects.filter(
                activity_id=response.data["id"],
                deleted_at__isnull=True,
            ).order_by("location_id", "crop_variety_id")
        )
        self.assertEqual(len(coverages), 2)
        self.assertEqual(coverages[0].location_id, self.location1.id)
        self.assertEqual(coverages[0].crop_variety_id, self.variety1.id)
        self.assertEqual(coverages[1].location_id, self.location2.id)
        self.assertEqual(coverages[1].crop_variety_id, self.variety2.id)

    def test_single_location_service_rows_may_omit_row_location_without_collapsing_multi_location_rules(self):
        url = reverse("activities-list")
        today_log = DailyLog.objects.create(farm=self.farm1, log_date=timezone.localdate())
        payload = {
            "log_id": today_log.id,
            "crop_id": self.crop.id,
            "task_id": self.task.id,
            "location_ids": [self.location1.id],
            "variety_id": self.variety1.id,
            "activity_tree_count": 10,
            "tree_count_delta": 0,
            "service_counts_payload": [
                {
                    "variety_id": self.variety1.id,
                    "service_count": 10,
                    "service_type": TreeServiceCoverage.GENERAL,
                }
            ],
        }

        response = self.client.post(url, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="key-single-location-row")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        coverage = TreeServiceCoverage.objects.get(
            activity_id=response.data["id"],
            deleted_at__isnull=True,
            crop_variety_id=self.variety1.id,
        )
        self.assertEqual(coverage.location_id, self.location1.id)

    def test_summary_export_returns_csv(self):
        url = reverse("tree-inventory-summary-export")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn(self.location1.name, content)
        self.assertIn("tree_inventory_summary", response["Content-Disposition"])

    def test_summary_respects_user_without_membership(self):
        client = APIClient()
        client.force_authenticate(self.other_user)
        response = client.get(reverse("tree-inventory-summary-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._extract_results(response.data)
        self.assertEqual(results, [])

    @override_settings(TREE_JUVENILE_YEARS="3 years", TREE_DECLINING_YEARS="18 years")
    def test_summary_handles_non_numeric_tree_threshold_settings(self):
        original_juvenile = TreeInventoryService.DEFAULT_JUVENILE_YEARS
        original_declining = TreeInventoryService.DEFAULT_DECLINING_YEARS
        try:
            TreeInventoryService.DEFAULT_JUVENILE_YEARS = settings.TREE_JUVENILE_YEARS
            TreeInventoryService.DEFAULT_DECLINING_YEARS = settings.TREE_DECLINING_YEARS
            response = self.client.get(reverse("tree-inventory-summary-list"))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        finally:
            TreeInventoryService.DEFAULT_JUVENILE_YEARS = original_juvenile
            TreeInventoryService.DEFAULT_DECLINING_YEARS = original_declining

    def test_events_list_supports_filters_and_permissions(self):
        url = reverse("tree-inventory-events-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._extract_results(response.data)
        self.assertEqual(len(results), 4)
        event_types = {item["event_type"] for item in results}
        self.assertIn(TreeStockEvent.PLANTING, event_types)
        self.assertIn(TreeStockEvent.LOSS, event_types)
        self.assertIn(TreeStockEvent.HARVEST, event_types)
        self.assertTrue(all(item["location_tree_stock"]["location"]["name"] != self.location3.name for item in results))

        loss_filtered = self.client.get(url, {"event_type": TreeStockEvent.LOSS})
        loss_results = self._extract_results(loss_filtered.data)
        self.assertEqual(len(loss_results), 1)
        self.assertEqual(loss_results[0]["loss_reason"]["code"], self.loss_reason.code)

        farm_filtered = self.client.get(url, {"farm_id": self.farm1.id})
        farm_results = self._extract_results(farm_filtered.data)
        self.assertEqual(len(farm_results), 4)

    def test_events_export_returns_csv(self):
        url = reverse("tree-inventory-events-export")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        body = response.content.decode("utf-8")
        self.assertIn(TreeStockEvent.LOSS, body)
        self.assertIn("tree_inventory_events", response["Content-Disposition"])

    def test_events_respect_missing_membership(self):
        client = APIClient()
        client.force_authenticate(self.other_user)
        response = client.get(reverse("tree-inventory-events-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._extract_results(response.data)
        self.assertEqual(results, [])
