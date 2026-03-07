import os, tempfile, time, pytest, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"))

from screenshot_manager import ScreenshotManager


class TestScreenshotManager:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mgr = ScreenshotManager(self.tmpdir, max_screenshots=5)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_returns_path(self):
        path = self.mgr.save(b"\x89PNG fake image data")
        assert os.path.exists(path)
        assert path.startswith(self.tmpdir)
        assert path.endswith(".png")

    def test_rolling_cap_purges_oldest(self):
        paths = []
        for i in range(7):
            p = self.mgr.save(f"image_{i}".encode())
            paths.append(p)
            time.sleep(0.01)
        remaining = self.mgr.list_screenshots()
        assert len(remaining) == 5
        assert not os.path.exists(paths[0])
        assert not os.path.exists(paths[1])
        for p in paths[2:]:
            assert os.path.exists(p)

    def test_cleanup_removes_all(self):
        for i in range(3):
            self.mgr.save(f"image_{i}".encode())
        removed = self.mgr.cleanup()
        assert removed == 3
        assert len(self.mgr.list_screenshots()) == 0

    def test_set_limit(self):
        for i in range(10):
            self.mgr.save(f"image_{i}".encode())
        self.mgr.set_limit(3)
        assert len(self.mgr.list_screenshots()) == 3

    def test_list_returns_sorted_newest_first(self):
        for i in range(3):
            self.mgr.save(f"image_{i}".encode())
            time.sleep(0.01)
        screenshots = self.mgr.list_screenshots()
        assert len(screenshots) == 3
        for i in range(len(screenshots) - 1):
            assert screenshots[i]["created"] >= screenshots[i + 1]["created"]

