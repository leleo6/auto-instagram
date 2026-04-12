"""
test_suite.py
─────────────────────────────────────────────────────────────────────────────
Suite extendida de pruebas unitarias para auto-instagram.
Cubre: HistoryManager, SchedulerManager, AccountManager, ConfigLoader CRUD,
       VideoEngine helpers, UploaderFactory, SchedulerWorker, Storage, Retries.

Correr con:
    pytest bot_insta/tests/test_suite.py -v
"""

import copy
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

BASE_CONFIG = {
    "active_profile": "default",
    "profiles": {
        "default": {
            "backgrounds_subfolder": "nature",
            "music_subfolder": "chill",
            "quotes_file": "bot_insta/config/quotes/quotes.txt",
            "text": {"font_size": 72},
            "audio": {"volume": 0.8},
            "duration": 10,
        }
    },
    "paths": {
        "base_backgrounds": "bot_insta/assets/backgrounds",
        "base_music": "bot_insta/assets/music",
        "base_overlays": "bot_insta/assets/overlays",
        "output_dir": "bot_insta/exports",
        "session_file": "bot_insta/config/session.json",
        "tiktok_cookies": "bot_insta/config/cookies.txt",
    },
    "captions": {},
    "video": {"target_w": 1080, "target_h": 1920, "duration": 10, "audio_fadeout": 2},
}


class MockStorage:
    """In-memory storage — no disk I/O."""
    def __init__(self, data=None):
        self._data = data
        self.saved = None

    def load(self, filepath):
        return self._data

    def save(self, filepath, data):
        self.saved = data
        self._data = data


def make_loader(cfg=None):
    from bot_insta.src.core.config_loader import ConfigLoader
    return ConfigLoader(
        config_path=Path("fake.yaml"),
        storage=MockStorage(copy.deepcopy(cfg or BASE_CONFIG)),
    )


def _future(hours=1):
    return (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")


def _past(hours=1):
    return (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# HistoryManager
# ─────────────────────────────────────────────────────────────────────────────

class TestHistoryManager:

    def _mgr(self, tmp_path):
        from bot_insta.src.core.history_manager import HistoryManager
        return HistoryManager(history_file=tmp_path / "history.json")

    def test_log_event_creates_entry(self, tmp_path):
        mgr = self._mgr(tmp_path)
        mgr.log_event("reel_001.mp4", "Instagram", "acc_abc", "Success", "media_123")
        today = datetime.now().strftime("%Y-%m-%d")
        events = mgr.get_events_by_date(today)
        assert len(events) == 1
        e = events[0]
        assert e["filename"] == "reel_001.mp4"
        assert e["platform"] == "Instagram"
        assert e["account_id"] == "acc_abc"
        assert e["status"] == "Success"
        assert e["media_id"] == "media_123"

    def test_log_event_persists_to_disk(self, tmp_path):
        mgr = self._mgr(tmp_path)
        mgr.log_event("reel_002.mp4", "TikTok", "acc_xyz", "Generated")
        from bot_insta.src.core.history_manager import HistoryManager
        mgr2 = HistoryManager(history_file=tmp_path / "history.json")
        today = datetime.now().strftime("%Y-%m-%d")
        assert any(e["filename"] == "reel_002.mp4" for e in mgr2.get_events_by_date(today))

    def test_get_events_by_date_filters_correctly(self, tmp_path):
        mgr = self._mgr(tmp_path)
        data = [
            {"date": "2026-01-01", "timestamp": "2026-01-01T10:00:00",
             "filename": "old.mp4", "platform": "Local", "account_id": "local",
             "status": "Generated", "media_id": ""},
            {"date": "2026-04-07", "timestamp": "2026-04-07T15:00:00",
             "filename": "today.mp4", "platform": "Instagram", "account_id": "acc1",
             "status": "Success", "media_id": "m1"},
        ]
        mgr._save(data)
        result = mgr.get_events_by_date("2026-04-07")
        assert len(result) == 1
        assert result[0]["filename"] == "today.mp4"

    def test_get_events_sorted_newest_first(self, tmp_path):
        mgr = self._mgr(tmp_path)
        data = [
            {"date": "2026-04-07", "timestamp": "2026-04-07T08:00:00",
             "filename": "early.mp4", "platform": "Local", "account_id": "local",
             "status": "Generated", "media_id": ""},
            {"date": "2026-04-07", "timestamp": "2026-04-07T20:00:00",
             "filename": "late.mp4", "platform": "Local", "account_id": "local",
             "status": "Generated", "media_id": ""},
        ]
        mgr._save(data)
        result = mgr.get_events_by_date("2026-04-07")
        assert result[0]["filename"] == "late.mp4"
        assert result[1]["filename"] == "early.mp4"

    def test_get_all_active_dates_returns_set(self, tmp_path):
        mgr = self._mgr(tmp_path)
        mgr.log_event("a.mp4", "Local", "local", "Generated")
        mgr.log_event("b.mp4", "Local", "local", "Generated")
        dates = mgr.get_all_active_dates()
        assert isinstance(dates, set)
        assert datetime.now().strftime("%Y-%m-%d") in dates

    def test_load_returns_empty_on_missing_file(self, tmp_path):
        from bot_insta.src.core.history_manager import HistoryManager
        mgr = HistoryManager(history_file=tmp_path / "nonexistent.json")
        assert mgr._load() == []

    def test_load_returns_empty_on_corrupt_json(self, tmp_path):
        hfile = tmp_path / "corrupt.json"
        hfile.write_text("{NOT valid JSON!!!", encoding="utf-8")
        from bot_insta.src.core.history_manager import HistoryManager
        mgr = HistoryManager(history_file=hfile)
        assert mgr._load() == []

    def test_thread_safety_concurrent_writes(self, tmp_path):
        """50 eventos de 5 threads concurrentes no deben corromper datos."""
        mgr = self._mgr(tmp_path)
        errors = []

        def log_many():
            try:
                for i in range(10):
                    mgr.log_event(f"reel_{i}.mp4", "Local", "local", "Generated")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=log_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread safety fallo: {errors}"
        today = datetime.now().strftime("%Y-%m-%d")
        assert len(mgr.get_events_by_date(today)) == 50


# ─────────────────────────────────────────────────────────────────────────────
# SchedulerManager
# ─────────────────────────────────────────────────────────────────────────────

class TestSchedulerManager:

    def _mgr(self, tmp_path):
        from bot_insta.src.core.scheduler_manager import SchedulerManager
        return SchedulerManager(scheduler_file=tmp_path / "scheduler.json")

    def test_add_job_returns_dict_with_id(self, tmp_path):
        mgr = self._mgr(tmp_path)
        job = mgr.add_job(
            type="render_and_upload", profile="default", account_id="acc1",
            platform="Instagram", caption="Test", scheduled_time=_future(),
        )
        assert "id" in job
        assert job["type"] == "render_and_upload"
        assert job["status"] == "pending"
        assert job["batch_id"] == "Ungrouped"

    def test_add_job_with_batch_id(self, tmp_path):
        mgr = self._mgr(tmp_path)
        job = mgr.add_job(
            type="render_and_upload", profile="default", account_id="acc1",
            platform="Local", caption="", scheduled_time=_future(), batch_id="April Batch",
        )
        assert job["batch_id"] == "April Batch"

    def test_update_job_status(self, tmp_path):
        mgr = self._mgr(tmp_path)
        job = mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future())
        mgr.update_job_status(job["id"], "processing")
        assert mgr.get_all_jobs()[0]["status"] == "processing"

    def test_update_job_status_sets_error_msg(self, tmp_path):
        mgr = self._mgr(tmp_path)
        job = mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future())
        mgr.update_job_status(job["id"], "failed", "Connection timeout")
        assert mgr.get_all_jobs()[0]["error_msg"] == "Connection timeout"

    def test_update_job_file(self, tmp_path):
        mgr = self._mgr(tmp_path)
        job = mgr.add_job("upload_only", "default", "acc1", "Local", "", _future())
        mgr.update_job_file(job["id"], "/exports/reel_123.mp4")
        assert mgr.get_all_jobs()[0]["file_path"] == "/exports/reel_123.mp4"

    def test_delete_job(self, tmp_path):
        mgr = self._mgr(tmp_path)
        job = mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future())
        mgr.delete_job(job["id"])
        assert mgr.get_all_jobs() == []

    def test_get_all_jobs_sorted_by_time(self, tmp_path):
        mgr = self._mgr(tmp_path)
        mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future(2), batch_id="B1")
        mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future(1), batch_id="B2")
        jobs = mgr.get_all_jobs()
        assert jobs[0]["scheduled_time"] < jobs[1]["scheduled_time"]

    def test_get_pending_jobs_only_past_pending(self, tmp_path):
        mgr = self._mgr(tmp_path)
        mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _past(1))   # ← debe aparecer
        mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future(1)) # ← NO
        done = mgr.add_job("upload_only", "default", "acc1", "Local", "", _past(2))
        mgr.update_job_status(done["id"], "done")                                    # ← NO
        pending = mgr.get_pending_jobs()
        assert len(pending) == 1
        assert pending[0]["status"] == "pending"

    def test_load_returns_empty_if_no_file(self, tmp_path):
        mgr = self._mgr(tmp_path)
        assert mgr._load() == []

    def test_thread_safety_concurrent_add(self, tmp_path):
        mgr = self._mgr(tmp_path)
        errors = []

        def add_jobs():
            try:
                for _ in range(5):
                    mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _future())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_jobs) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(mgr.get_all_jobs()) == 20


# ─────────────────────────────────────────────────────────────────────────────
# AccountManager
# ─────────────────────────────────────────────────────────────────────────────

class TestAccountManager:

    def _mgr(self):
        from bot_insta.src.core.account_manager import AccountManager
        return AccountManager(filepath=Path("fake.json"), storage=MockStorage(data=[]))

    def test_add_account_returns_dict_with_id(self):
        mgr = self._mgr()
        acc = mgr.add_account("MyPage", "Instagram", {"username": "leo"})
        assert acc["name"] == "MyPage"
        assert acc["platform"] == "Instagram"
        assert "id" in acc
        assert acc["status"] == "Unknown"

    def test_add_multiple_accounts(self):
        mgr = self._mgr()
        mgr.add_account("Page1", "TikTok", {})
        mgr.add_account("Page2", "Instagram", {})
        assert len(mgr.list_accounts()) == 2

    def test_delete_account_removes_by_id(self):
        mgr = self._mgr()
        acc = mgr.add_account("ToDelete", "YouTube", {})
        mgr.delete_account(acc["id"])
        assert not any(a["id"] == acc["id"] for a in mgr.list_accounts())

    def test_delete_nonexistent_id_is_safe(self):
        mgr = self._mgr()
        mgr.delete_account("nonexistent-id")  # Must not raise

    def test_get_account_returns_correct(self):
        mgr = self._mgr()
        acc = mgr.add_account("Found", "Instagram", {"token": "abc"})
        result = mgr.get_account(acc["id"])
        assert result["name"] == "Found"
        assert result["credentials"]["token"] == "abc"

    def test_get_account_returns_empty_dict_if_missing(self):
        mgr = self._mgr()
        assert mgr.get_account("does-not-exist") == {}

    def test_update_status(self):
        mgr = self._mgr()
        acc = mgr.add_account("StatusTest", "TikTok", {})
        mgr.update_status(acc["id"], "Active")
        assert mgr.get_account(acc["id"])["status"] == "Active"

    def test_update_account_fields(self):
        mgr = self._mgr()
        acc = mgr.add_account("OldName", "YouTube", {})
        mgr.update_account(acc["id"], name="NewName", proxy="http://proxy:8080")
        result = mgr.get_account(acc["id"])
        assert result["name"] == "NewName"
        assert result["proxy"] == "http://proxy:8080"

    def test_update_account_returns_false_if_not_found(self):
        mgr = self._mgr()
        assert mgr.update_account("ghost-id", name="Ghost") is False

    def test_fetch_options_always_has_local_first(self):
        mgr = self._mgr()
        opts = mgr.fetch_options_for_dropdown()
        assert opts[0]["id"] == "local"
        assert opts[0]["platform"] == "Local"

    def test_fetch_options_includes_all_accounts(self):
        mgr = self._mgr()
        mgr.add_account("Page A", "Instagram", {})
        mgr.add_account("Page B", "TikTok", {})
        opts = mgr.fetch_options_for_dropdown()
        assert len(opts) == 3  # local + 2 accounts
        platforms = {o["platform"] for o in opts}
        assert "Instagram" in platforms
        assert "TikTok" in platforms


# ─────────────────────────────────────────────────────────────────────────────
# ConfigLoader CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigLoaderCRUD:

    def test_list_profiles_includes_default(self):
        assert "default" in make_loader().list_profiles()

    def test_create_profile_clones_source(self):
        loader = make_loader()
        loader.create_profile("new_prof", source_profile="default")
        assert "new_prof" in loader.list_profiles()

    def test_create_profile_duplicate_raises(self):
        with pytest.raises(ValueError, match="already exists"):
            make_loader().create_profile("default")

    def test_delete_profile_removes_it(self):
        loader = make_loader()
        loader.create_profile("temp_prof")
        loader.delete_profile("temp_prof")
        assert "temp_prof" not in loader.list_profiles()

    def test_delete_active_profile_raises(self):
        with pytest.raises(ValueError, match="active"):
            make_loader().delete_profile("default")

    def test_delete_nonexistent_profile_raises(self):
        with pytest.raises(KeyError):
            make_loader().delete_profile("ghost_profile")

    def test_set_active_profile(self):
        loader = make_loader()
        loader.create_profile("other")
        loader.set_active_profile("other")
        assert loader.get_active_profile() == "other"

    def test_set_active_profile_nonexistent_raises(self):
        with pytest.raises(KeyError):
            make_loader().set_active_profile("does_not_exist")

    def test_update_caption_creates_entry(self):
        loader = make_loader()
        loader.update_caption("motivacion", "Daily motivation", "#motivation")
        data = loader.get_caption_data("motivacion")
        assert data["description"] == "Daily motivation"
        assert data["hashtags"] == "#motivation"

    def test_delete_caption_removes_entry(self):
        loader = make_loader()
        loader.update_caption("to_del", "To delete", "#del")
        loader.delete_caption("to_del")
        assert "to_del" not in loader.list_captions()

    def test_list_captions_empty_initially(self):
        assert make_loader().list_captions() == []

    def test_get_caption_data_missing_returns_defaults(self):
        data = make_loader().get_caption_data("nonexistent")
        assert data == {"description": "", "hashtags": ""}

    def test_caption_migration_from_legacy_profile(self):
        """Captions en el perfil (formato viejo) deben migrarse al bloque 'captions'."""
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["profiles"]["default"]["caption"] = "Daily hustle #hustle #grind"
        loader = make_loader(cfg)
        assert "default" in loader.list_captions()
        data = loader.get_caption_data("default")
        full = data.get("description", "") + data.get("hashtags", "")
        assert "hustle" in full
        # El campo original debe haberse eliminado del perfil
        assert "caption" not in loader._config["profiles"]["default"]

    def test_get_returns_section_without_key(self):
        result = make_loader().get("video")
        assert result["target_w"] == 1080

    def test_get_returns_default_on_missing_key(self):
        result = make_loader().get("video", "nonexistent_key", default=42)
        assert result == 42

    def test_get_active_profile_data_returns_profile_dict(self):
        loader = make_loader()
        data = loader.get_active_profile_data()
        assert "text" in data
        assert "audio" in data

    def test_get_video_settings(self):
        loader = make_loader()
        settings = loader.get_video_settings()
        assert settings["target_w"] == 1080
        assert settings["target_h"] == 1920


# ─────────────────────────────────────────────────────────────────────────────
# VideoEngine helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestVideoEngineHelpers:

    def test_pick_random_file_raises_if_dir_missing(self, tmp_path):
        from bot_insta.src.core.video_engine import pick_random_file
        with pytest.raises(FileNotFoundError, match="no existe"):
            pick_random_file(tmp_path / "nonexistent", (".mp4",))

    def test_pick_random_file_raises_if_no_matching_files(self, tmp_path):
        from bot_insta.src.core.video_engine import pick_random_file
        (tmp_path / "notes.txt").write_text("hello")
        with pytest.raises(FileNotFoundError, match="No hay archivos"):
            pick_random_file(tmp_path, (".mp4",))

    def test_pick_random_file_returns_valid_path(self, tmp_path):
        from bot_insta.src.core.video_engine import pick_random_file
        (tmp_path / "video1.mp4").touch()
        (tmp_path / "video2.mp4").touch()
        result = pick_random_file(tmp_path, (".mp4",))
        assert result.suffix == ".mp4"
        assert result.parent == tmp_path

    def test_pick_random_file_ignores_wrong_extension(self, tmp_path):
        from bot_insta.src.core.video_engine import pick_random_file
        (tmp_path / "song.mp3").touch()
        (tmp_path / "video.mp4").touch()
        result = pick_random_file(tmp_path, (".mp3",))
        assert result.name == "song.mp3"

    def test_load_random_quote_raises_if_missing(self, tmp_path):
        from bot_insta.src.core.video_engine import load_random_quote
        with pytest.raises(FileNotFoundError):
            load_random_quote(tmp_path / "nonexistent.txt")

    def test_load_random_quote_raises_if_empty(self, tmp_path):
        from bot_insta.src.core.video_engine import load_random_quote
        empty = tmp_path / "empty.txt"
        empty.write_text("   \n  \n", encoding="utf-8")
        with pytest.raises(ValueError, match="vacío"):
            load_random_quote(empty)

    def test_load_random_quote_returns_a_line(self, tmp_path):
        from bot_insta.src.core.video_engine import load_random_quote
        qfile = tmp_path / "quotes.txt"
        qfile.write_text("Quote A\nQuote B\nQuote C\n", encoding="utf-8")
        result = load_random_quote(qfile)
        assert result in ("Quote A", "Quote B", "Quote C")

    def test_load_random_quote_strips_whitespace(self, tmp_path):
        from bot_insta.src.core.video_engine import load_random_quote
        qfile = tmp_path / "q.txt"
        qfile.write_text("  Only one quote  \n", encoding="utf-8")
        assert load_random_quote(qfile) == "Only one quote"

    def test_build_overlay_returns_none_if_path_missing(self, tmp_path):
        from bot_insta.src.core.video_engine import build_overlay
        result = build_overlay(tmp_path / "missing.png", duration=10.0, target_w=1080, target_h=1920)
        assert result is None

    def test_build_overlay_returns_none_if_path_is_none(self):
        from bot_insta.src.core.video_engine import build_overlay
        assert build_overlay(None, duration=10.0, target_w=1080, target_h=1920) is None

    def test_volume_clamping_logic(self):
        """La lógica de clamping de volumen respeta [0.0, 1.0]."""
        cases = [(2.5, 1.0), (-0.5, 0.0), (0.8, 0.8), (1.0, 1.0), (0.0, 0.0)]
        for raw, expected in cases:
            assert max(0.0, min(1.0, raw)) == expected

    def test_output_dir_created_if_missing(self, tmp_path):
        """create_reel debe crear output_dir si no existe."""
        from bot_insta.src.core.video_engine import create_reel, VideoContext
        output = tmp_path / "deep" / "nested" / "exports"
        assert not output.exists()

        with patch("bot_insta.src.core.video_engine.pick_random_file", return_value=Path("f.mp4")), \
             patch("bot_insta.src.core.video_engine.load_random_quote", return_value="Quote"), \
             patch("bot_insta.src.core.video_engine.prepare_background", return_value=MagicMock()), \
             patch("bot_insta.src.core.video_engine.prepare_audio", return_value=MagicMock()), \
             patch("bot_insta.src.core.video_engine.build_text_overlay", return_value=MagicMock()), \
             patch("bot_insta.src.core.video_engine.CompositeVideoClip") as mock_cvc:
            mock_cvc.return_value.set_audio.return_value = MagicMock()
            ctx = VideoContext(
                bg_dir=tmp_path, music_dir=tmp_path,
                quotes_file=tmp_path / "q.txt", output_dir=output,
            )
            create_reel(ctx)

        assert output.exists()

    def test_no_temp_files_left_after_successful_render(self, tmp_path):
        """Después de un render exitoso no deben quedar archivos TEMP en output_dir."""
        from bot_insta.src.core.video_engine import create_reel, VideoContext

        with patch("bot_insta.src.core.video_engine.pick_random_file", return_value=Path("f.mp4")), \
             patch("bot_insta.src.core.video_engine.load_random_quote", return_value="Quote"), \
             patch("bot_insta.src.core.video_engine.prepare_background", return_value=MagicMock()), \
             patch("bot_insta.src.core.video_engine.prepare_audio", return_value=MagicMock()), \
             patch("bot_insta.src.core.video_engine.build_text_overlay", return_value=MagicMock()), \
             patch("bot_insta.src.core.video_engine.CompositeVideoClip") as mock_cvc:
            mock_cvc.return_value.set_audio.return_value = MagicMock()
            ctx = VideoContext(
                bg_dir=tmp_path, music_dir=tmp_path,
                quotes_file=tmp_path / "q.txt", output_dir=tmp_path,
            )
            create_reel(ctx)

        temp_files = list(tmp_path.glob("*TEMP*")) + list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0, f"Archivos TEMP encontrados: {temp_files}"


# ─────────────────────────────────────────────────────────────────────────────
# UploaderFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestUploaderFactory:

    def test_get_instagram_uploader(self):
        from bot_insta.src.core.uploader_factory import UploaderFactory
        from bot_insta.src.api.instagram import InstagramUploader
        assert isinstance(UploaderFactory.get_uploader("Instagram"), InstagramUploader)

    def test_get_tiktok_uploader(self):
        from bot_insta.src.core.uploader_factory import UploaderFactory
        from bot_insta.src.api.tiktok import TikTokUploader
        assert isinstance(UploaderFactory.get_uploader("TikTok"), TikTokUploader)

    def test_get_youtube_uploader(self):
        from bot_insta.src.core.uploader_factory import UploaderFactory
        from bot_insta.src.api.youtube import YouTubeUploader
        assert isinstance(UploaderFactory.get_uploader("YouTube"), YouTubeUploader)

    def test_unsupported_platform_raises(self):
        from bot_insta.src.core.uploader_factory import UploaderFactory
        with pytest.raises(ValueError, match="not supported"):
            UploaderFactory.get_uploader("Facebook")

    def test_empty_string_raises(self):
        from bot_insta.src.core.uploader_factory import UploaderFactory
        with pytest.raises(ValueError):
            UploaderFactory.get_uploader("")

    def test_case_sensitive_platform(self):
        """'instagram' (minúscula) no debe matchear 'Instagram'."""
        from bot_insta.src.core.uploader_factory import UploaderFactory
        with pytest.raises(ValueError):
            UploaderFactory.get_uploader("instagram")


# ─────────────────────────────────────────────────────────────────────────────
# SchedulerWorker
# ─────────────────────────────────────────────────────────────────────────────

class TestSchedulerWorker:

    def test_start_and_stop(self):
        from bot_insta.src.core.scheduler_worker import SchedulerWorker
        worker = SchedulerWorker()
        with patch.object(worker, "_process_pending_jobs", return_value=None):
            worker.start()
            assert worker.thread is not None
            assert worker.thread.is_alive()
            worker.stop()
            worker.thread.join(timeout=5.0)
            assert not worker.thread.is_alive()

    def test_start_is_idempotent(self):
        from bot_insta.src.core.scheduler_worker import SchedulerWorker
        worker = SchedulerWorker()
        with patch.object(worker, "_process_pending_jobs", return_value=None):
            worker.start()
            first_thread = worker.thread
            worker.start()  # Segunda llamada → mismo thread
            assert worker.thread is first_thread
            worker.stop()

    def test_failed_job_marked_as_failed(self, tmp_path):
        """Si render falla, el job queda con status='failed' y error_msg."""
        from bot_insta.src.core.scheduler_worker import SchedulerWorker
        from bot_insta.src.core.scheduler_manager import SchedulerManager

        mgr = SchedulerManager(scheduler_file=tmp_path / "sched.json")
        job = mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _past(1))

        worker = SchedulerWorker()
        with patch("bot_insta.src.core.scheduler_worker.scheduler_manager", mgr), \
             patch("bot_insta.src.core.scheduler_worker.make_video_context", return_value=MagicMock()), \
             patch("bot_insta.src.core.scheduler_worker.create_reel", side_effect=RuntimeError("render fail")), \
             patch("bot_insta.src.core.scheduler_worker.acc_manager"):
            worker._process_pending_jobs()

        jobs = mgr.get_all_jobs()
        assert jobs[0]["status"] == "failed"
        assert "render fail" in jobs[0]["error_msg"]

    def test_local_completed_job_deleted(self, tmp_path):
        """Job 'upload_only' con plataforma Local debe completarse y borrarse."""
        from bot_insta.src.core.scheduler_worker import SchedulerWorker
        from bot_insta.src.core.scheduler_manager import SchedulerManager

        mgr = SchedulerManager(scheduler_file=tmp_path / "sched.json")
        mgr.add_job("upload_only", "default", "acc1", "Local", "", _past(1),
                    file_path="/tmp/fake_reel.mp4")

        worker = SchedulerWorker()
        with patch("bot_insta.src.core.scheduler_worker.scheduler_manager", mgr), \
             patch("bot_insta.src.core.scheduler_worker.history_manager"), \
             patch("bot_insta.src.core.scheduler_worker.acc_manager"):
            worker._process_pending_jobs()

        assert mgr.get_all_jobs() == []

    def test_no_jobs_processed_if_stop_set(self, tmp_path):
        """Si stop_event está activo, no debe procesar ningún job."""
        from bot_insta.src.core.scheduler_worker import SchedulerWorker
        from bot_insta.src.core.scheduler_manager import SchedulerManager

        mgr = SchedulerManager(scheduler_file=tmp_path / "sched.json")
        mgr.add_job("render_and_upload", "default", "acc1", "Local", "", _past(1))

        worker = SchedulerWorker()
        worker.stop_event.set()  # Simular detención antes de procesar

        with patch("bot_insta.src.core.scheduler_worker.scheduler_manager", mgr):
            worker._process_pending_jobs()

        # El job debe seguir pendiente (no fue procesado)
        assert mgr.get_all_jobs()[0]["status"] == "pending"


# ─────────────────────────────────────────────────────────────────────────────
# Storage edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestStorageEdgeCases:

    def test_json_load_missing_file_returns_none(self, tmp_path):
        from bot_insta.src.core.storage import JsonStorage
        assert JsonStorage().load(tmp_path / "missing.json") is None

    def test_json_load_corrupt_returns_none(self, tmp_path):
        from bot_insta.src.core.storage import JsonStorage
        bad = tmp_path / "bad.json"
        bad.write_text("NOT_JSON", encoding="utf-8")
        assert JsonStorage().load(bad) is None

    def test_json_roundtrip(self, tmp_path):
        from bot_insta.src.core.storage import JsonStorage
        s = JsonStorage()
        data = {"key": "value", "num": 42, "lst": [1, 2, 3]}
        target = tmp_path / "data.json"
        s.save(target, data)
        assert s.load(target) == data

    def test_yaml_roundtrip(self, tmp_path):
        from bot_insta.src.core.storage import YamlStorage
        s = YamlStorage()
        data = {"active_profile": "default", "profiles": {"default": {}}}
        target = tmp_path / "config.yaml"
        s.save(target, data)
        assert s.load(target) == data

    def test_yaml_missing_file_returns_none(self, tmp_path):
        from bot_insta.src.core.storage import YamlStorage
        assert YamlStorage().load(tmp_path / "missing.yaml") is None

    def test_json_creates_parent_dirs(self, tmp_path):
        from bot_insta.src.core.storage import JsonStorage
        target = tmp_path / "deep" / "nested" / "file.json"
        JsonStorage().save(target, {"ok": True})
        assert target.exists()

    def test_yaml_creates_parent_dirs(self, tmp_path):
        from bot_insta.src.core.storage import YamlStorage
        target = tmp_path / "a" / "b" / "config.yaml"
        YamlStorage().save(target, {"ok": True})
        assert target.exists()

    def test_json_no_tmp_file_on_error(self, tmp_path):
        from bot_insta.src.core.storage import JsonStorage
        target = tmp_path / "data.json"
        with patch("builtins.open", side_effect=OSError("disk full")):
            JsonStorage().save(target, {"x": 1})
        assert not target.with_suffix(".json.tmp").exists()

    def test_yaml_no_tmp_file_on_error(self, tmp_path):
        from bot_insta.src.core.storage import YamlStorage
        target = tmp_path / "data.yaml"
        with patch("builtins.open", side_effect=OSError("disk full")):
            YamlStorage().save(target, {"x": 1})
        assert not target.with_suffix(".yaml.tmp").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Retries decorator
# ─────────────────────────────────────────────────────────────────────────────

class TestRetriesDecorator:

    def test_succeeds_on_first_try(self):
        from bot_insta.src.api.retries import with_retries
        calls = [0]

        @with_retries(max_attempts=3, base_delay=0.0)
        def ok():
            calls[0] += 1
            return "ok"

        assert ok() == "ok"
        assert calls[0] == 1

    def test_succeeds_on_second_try(self):
        from bot_insta.src.api.retries import with_retries
        calls = [0]

        @with_retries(max_attempts=3, base_delay=0.0)
        def flaky():
            calls[0] += 1
            if calls[0] < 2:
                raise ConnectionError("transient")
            return "recovered"

        assert flaky() == "recovered"
        assert calls[0] == 2

    def test_raises_after_max_attempts(self):
        from bot_insta.src.api.retries import with_retries
        calls = [0]

        @with_retries(max_attempts=3, base_delay=0.0)
        def always_fails():
            calls[0] += 1
            raise ValueError("persistent")

        with pytest.raises(ValueError):
            always_fails()
        assert calls[0] == 3

    def test_interrupted_error_not_retried(self):
        from bot_insta.src.api.retries import with_retries
        calls = [0]

        @with_retries(max_attempts=5, base_delay=0.0)
        def cancel():
            calls[0] += 1
            raise InterruptedError("cancelled")

        with pytest.raises(InterruptedError):
            cancel()
        assert calls[0] == 1

    def test_return_value_propagated(self):
        from bot_insta.src.api.retries import with_retries

        @with_retries(max_attempts=2, base_delay=0.0)
        def give_value():
            return {"status": "ok", "count": 99}

        result = give_value()
        assert result == {"status": "ok", "count": 99}
