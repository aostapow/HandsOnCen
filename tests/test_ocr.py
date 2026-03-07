# tests/test_ocr.py
"""Tests for OCR text targeting."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


@mock.patch("tools.ocr._capture_image_path", return_value="/fake/screenshot.png")
class TestOcrEngine:
    @mock.patch("tools.ocr._run_ocr")
    def test_find_text_returns_matches(self, mock_ocr, _mock_cap):
        mock_ocr.return_value = [
            {"text": "Search or enter web address", "x": 200, "y": 30, "width": 300, "height": 20},
            {"text": "Settings", "x": 1400, "y": 50, "width": 60, "height": 18},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Search")
        assert len(result["matches"]) == 1
        assert result["matches"][0]["text"] == "Search or enter web address"

    @mock.patch("tools.ocr._run_ocr")
    def test_find_text_case_insensitive(self, mock_ocr, _mock_cap):
        mock_ocr.return_value = [
            {"text": "SUBMIT", "x": 100, "y": 100, "width": 80, "height": 25},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("submit")
        assert len(result["matches"]) == 1

    @mock.patch("tools.ocr._run_ocr")
    def test_find_text_no_match(self, mock_ocr, _mock_cap):
        mock_ocr.return_value = [
            {"text": "Hello World", "x": 100, "y": 100, "width": 80, "height": 25},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Goodbye")
        assert len(result["matches"]) == 0


class TestClickText:
    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_click_first_match(self, mock_find, mock_click):
        mock_find.return_value = {
            "matches": [
                {"text": "OK", "x": 100, "y": 200, "width": 60, "height": 25},
                {"text": "OK", "x": 300, "y": 200, "width": 60, "height": 25},
            ]
        }
        mock_click.return_value = {"action": "click"}

        from tools.ocr import do_click_text
        result = do_click_text("OK", occurrence=1)

        # Center of first match: 100+30=130, 200+12=212
        mock_click.assert_called_once_with(130, 212)

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_click_second_occurrence(self, mock_find, mock_click):
        mock_find.return_value = {
            "matches": [
                {"text": "OK", "x": 100, "y": 200, "width": 60, "height": 25},
                {"text": "OK", "x": 300, "y": 200, "width": 60, "height": 25},
            ]
        }
        mock_click.return_value = {"action": "click"}

        from tools.ocr import do_click_text
        result = do_click_text("OK", occurrence=2)

        # Center of second match: 300+30=330, 200+12=212
        mock_click.assert_called_once_with(330, 212)

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_no_retry_when_visual_change(self, mock_find, mock_click):
        """When center click produces visual change, no retry occurs."""
        mock_find.return_value = {
            "matches": [{"text": "Submit", "x": 100, "y": 200, "width": 80, "height": 30}]
        }
        mock_click.return_value = {"action": "click", "visual_change": True, "pixel_diff": 0.05}

        from tools.ocr import do_click_text
        result = do_click_text("Submit")

        mock_click.assert_called_once_with(140, 215)
        assert "retry" not in result

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_retry_below_on_no_change(self, mock_find, mock_click):
        """When center click has no visual change, retries below and succeeds."""
        mock_find.return_value = {
            "matches": [{"text": "Title", "x": 100, "y": 200, "width": 40, "height": 18}]
        }
        # First click (center): no change. Second click (below): change detected.
        mock_click.side_effect = [
            {"action": "click", "visual_change": False, "pixel_diff": 0.001},
            {"action": "click", "visual_change": True, "pixel_diff": 0.03},
        ]

        from tools.ocr import do_click_text
        result = do_click_text("Title")

        assert result["retry"] == "below"
        # Offset = max(60, 18*3) = 60; center_y=209, so retry at 209+60=269
        assert result["clicked_at"]["y"] == 269
        assert mock_click.call_count == 2

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_retry_above_when_below_fails(self, mock_find, mock_click):
        """When both below offsets fail, retries above."""
        mock_find.return_value = {
            "matches": [{"text": "Label", "x": 100, "y": 200, "width": 50, "height": 20}]
        }
        # Center: no. Below close: no. Below far: no. Above close: yes.
        mock_click.side_effect = [
            {"action": "click", "visual_change": False, "pixel_diff": 0.0},
            {"action": "click", "visual_change": False, "pixel_diff": 0.0},
            {"action": "click", "visual_change": False, "pixel_diff": 0.0},
            {"action": "click", "visual_change": True, "pixel_diff": 0.02},
        ]

        from tools.ocr import do_click_text
        result = do_click_text("Label")

        assert result["retry"] == "above"
        assert mock_click.call_count == 4

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_all_retries_fail(self, mock_find, mock_click):
        """When all offsets fail, returns none_worked."""
        mock_find.return_value = {
            "matches": [{"text": "Ghost", "x": 100, "y": 500, "width": 50, "height": 20}]
        }
        mock_click.return_value = {"action": "click", "visual_change": False, "pixel_diff": 0.0}

        from tools.ocr import do_click_text
        result = do_click_text("Ghost")

        assert result["retry"] == "none_worked"
        # 1 center + 6 offsets (below, below_far, above, above_far, right, left) = 7
        assert mock_click.call_count == 7

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_offset_scales_with_text_height(self, mock_find, mock_click):
        """Small offset is max(60, height*3) — large text gets larger offsets."""
        mock_find.return_value = {
            "matches": [{"text": "BIG", "x": 100, "y": 200, "width": 100, "height": 40}]
        }
        # Center: no change. Below (small): change.
        mock_click.side_effect = [
            {"action": "click", "visual_change": False, "pixel_diff": 0.0},
            {"action": "click", "visual_change": True, "pixel_diff": 0.05},
        ]

        from tools.ocr import do_click_text
        result = do_click_text("BIG")

        # small offset = max(60, 40*3) = 120; center_y=220, retry at 220+120=340
        assert result["clicked_at"]["y"] == 340
        assert result["retry"] == "below"

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_far_offset_on_small_text(self, mock_find, mock_click):
        """When close below fails, tries far below (max(250, height*15))."""
        mock_find.return_value = {
            "matches": [{"text": "Label", "x": 100, "y": 200, "width": 40, "height": 18}]
        }
        # Center: no change. Below close: no change. Below far: change.
        mock_click.side_effect = [
            {"action": "click", "visual_change": False, "pixel_diff": 0.0},
            {"action": "click", "visual_change": False, "pixel_diff": 0.0},
            {"action": "click", "visual_change": True, "pixel_diff": 0.03},
        ]

        from tools.ocr import do_click_text
        result = do_click_text("Label")

        # large offset = max(250, 18*15) = 270; center_y=209, retry at 209+270=479
        assert result["clicked_at"]["y"] == 479
        assert result["retry"] == "below_far"


class TestDarkBackgroundOcr:
    @mock.patch("tools.ocr.os.remove")
    @mock.patch("tools.ocr.ImageOps.invert")
    @mock.patch("tools.ocr.Image.open")
    @mock.patch("tools.ocr._run_ocr_engine")
    def test_invert_flag_creates_inverted_image(self, mock_engine, mock_open, mock_invert, mock_remove):
        """_run_ocr(invert=True) should invert the image before OCR."""
        from tools.ocr import _run_ocr

        mock_engine.return_value = [
            {"text": "Settings", "x": 100, "y": 50, "width": 80, "height": 20}
        ]
        mock_open.return_value.convert.return_value = mock.MagicMock()
        mock_invert.return_value = mock.MagicMock()

        results = _run_ocr("/fake/screenshot.png", invert=True)
        assert len(results) == 1
        assert results[0]["text"] == "Settings"
        mock_invert.assert_called_once()

    @mock.patch("tools.ocr._run_ocr_engine")
    def test_no_invert_flag_skips_inversion(self, mock_engine):
        """_run_ocr(invert=False) should not invert."""
        from tools.ocr import _run_ocr

        mock_engine.return_value = [
            {"text": "Hello", "x": 10, "y": 10, "width": 50, "height": 20}
        ]

        results = _run_ocr("/fake/screenshot.png", invert=False)
        assert len(results) == 1
        assert mock_engine.call_count == 1


@mock.patch("tools.ocr._capture_image_path", return_value="/fake/screenshot.png")
class TestQueryAwareDarkBgRetry:
    @mock.patch("tools.ocr._run_ocr")
    def test_inversion_tried_when_query_not_found(self, mock_ocr, _mock_cap):
        """When query not found in normal results, inverted OCR should be tried."""
        from tools.ocr import do_find_text

        # First call returns words but NOT the target; second returns the target
        mock_ocr.side_effect = [
            [{"text": "Light", "x": 100, "y": 50, "width": 50, "height": 20}],
            [{"text": "Dark", "x": 200, "y": 300, "width": 40, "height": 18}],
        ]

        result = do_find_text("Dark")
        assert len(result["matches"]) == 1
        assert result["matches"][0]["text"] == "Dark"
        assert mock_ocr.call_count == 2  # Normal + inverted

    @mock.patch("tools.ocr._run_ocr")
    def test_always_runs_both_passes(self, mock_ocr, _mock_cap):
        """Both normal and inverted passes always run (dual-pass merge)."""
        from tools.ocr import do_find_text

        mock_ocr.side_effect = [
            [{"text": "Hello", "x": 10, "y": 10, "width": 50, "height": 20}],
            [],  # inverted pass finds nothing extra
        ]

        result = do_find_text("Hello")
        assert len(result["matches"]) == 1
        assert mock_ocr.call_count == 2  # Normal + inverted always

    @mock.patch("tools.ocr._run_ocr")
    def test_inverted_results_merged_and_deduplicated(self, mock_ocr, _mock_cap):
        """Results from both passes should be merged and deduplicated."""
        from tools.ocr import do_find_text

        # Normal pass finds "File", inverted pass finds "File" (dup) and "Dark"
        mock_ocr.side_effect = [
            [{"text": "File", "x": 10, "y": 10, "width": 40, "height": 20}],
            [
                {"text": "File", "x": 10, "y": 10, "width": 40, "height": 20},
                {"text": "Dark", "x": 200, "y": 50, "width": 50, "height": 20},
            ],
        ]

        result = do_find_text("Dark")
        assert len(result["matches"]) == 1
        # total_words should include deduplicated words from both passes
        assert result["total_words"] == 2  # File + Dark (deduplicated)

    @mock.patch("tools.ocr._run_ocr")
    def test_always_merge_finds_dark_bg_text_with_partial_normal(self, mock_ocr, _mock_cap):
        """Normal pass finds some words but not target; inverted finds target."""
        from tools.ocr import do_find_text

        # Normal: finds "Light" and "Button" but NOT "Install"
        # Inverted: finds "Install" (dark bg text)
        mock_ocr.side_effect = [
            [
                {"text": "Light", "x": 100, "y": 50, "width": 50, "height": 20},
                {"text": "Button", "x": 200, "y": 50, "width": 60, "height": 20},
            ],
            [
                {"text": "Install", "x": 300, "y": 400, "width": 70, "height": 22},
            ],
        ]

        result = do_find_text("Install")
        assert len(result["matches"]) == 1
        assert result["matches"][0]["text"] == "Install"
        assert result["total_words"] == 3  # Light + Button + Install


@mock.patch("tools.ocr._capture_image_path", return_value="/fake/screenshot.png")
class TestPhraseMatching:
    @mock.patch("tools.ocr._run_ocr")
    def test_multi_word_query_matches_adjacent_words(self, mock_ocr, _mock_cap):
        """'Effective Stress' should match adjacent 'Effective' + 'Stress' words."""
        mock_ocr.return_value = [
            {"text": "Effective", "x": 100, "y": 50, "width": 80, "height": 20},
            {"text": "Stress", "x": 185, "y": 50, "width": 60, "height": 20},
            {"text": "Other", "x": 400, "y": 50, "width": 50, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Effective Stress")
        assert len(result["matches"]) == 1
        match = result["matches"][0]
        assert match["text"] == "Effective Stress"
        # Bounding box should span both words
        assert match["x"] == 100
        assert match["width"] == 185 + 60 - 100  # 145

    @mock.patch("tools.ocr._run_ocr")
    def test_single_word_query_still_works(self, mock_ocr, _mock_cap):
        """Single-word queries should work exactly as before."""
        mock_ocr.return_value = [
            {"text": "Settings", "x": 100, "y": 50, "width": 80, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Settings")
        assert len(result["matches"]) == 1
        assert result["matches"][0]["text"] == "Settings"

    @mock.patch("tools.ocr._run_ocr")
    def test_phrase_not_found_when_words_on_different_lines(self, mock_ocr, _mock_cap):
        """Words on different lines should not form a phrase match."""
        mock_ocr.return_value = [
            {"text": "Effective", "x": 100, "y": 50, "width": 80, "height": 20},
            {"text": "Stress", "x": 100, "y": 200, "width": 60, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Effective Stress")
        assert len(result["matches"]) == 0

    @mock.patch("tools.ocr._run_ocr")
    def test_three_word_phrase(self, mock_ocr, _mock_cap):
        mock_ocr.return_value = [
            {"text": "Save", "x": 100, "y": 50, "width": 40, "height": 20},
            {"text": "As", "x": 145, "y": 50, "width": 25, "height": 20},
            {"text": "PDF", "x": 175, "y": 50, "width": 35, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Save As PDF")
        assert len(result["matches"]) == 1
        assert result["matches"][0]["text"] == "Save As PDF"


class TestAdaptiveGapTolerance:
    def test_large_font_uses_wider_gap(self):
        """Words with large height (high-DPI/big font) should tolerate wider gaps."""
        from tools.ocr import _build_phrases

        # Simulate high-DPI: words are 40px tall with a 50px gap between them
        words = [
            {"text": "What", "x": 100, "y": 50, "width": 80, "height": 40},
            {"text": "It", "x": 230, "y": 50, "width": 40, "height": 40},
            {"text": "Does", "x": 320, "y": 50, "width": 70, "height": 40},
        ]
        phrases = _build_phrases(words)

        # gap_tolerance should be max(30, 40*1.5=60), so 50px gap should be joined
        assert len(phrases) == 1
        assert phrases[0]["text"] == "What It Does"

    def test_small_font_uses_tight_gap(self):
        """Small words should still separate when gap is large relative to height."""
        from tools.ocr import _build_phrases

        words = [
            {"text": "File", "x": 10, "y": 5, "width": 30, "height": 12},
            {"text": "Edit", "x": 200, "y": 5, "width": 30, "height": 12},
        ]
        phrases = _build_phrases(words)

        # gap_tolerance = max(30, 12*1.5=18) = 30. Gap is 200-40=160, way beyond.
        assert len(phrases) == 2

    def test_explicit_tolerance_overrides_adaptive(self):
        """Explicit gap_tolerance should override the adaptive default."""
        from tools.ocr import _build_phrases

        words = [
            {"text": "A", "x": 100, "y": 50, "width": 40, "height": 40},
            {"text": "B", "x": 200, "y": 50, "width": 40, "height": 40},
        ]
        # Gap is 60px. Adaptive would allow it (40*1.5=60), but explicit 10 rejects it.
        phrases = _build_phrases(words, gap_tolerance=10)
        assert len(phrases) == 2


class TestRapidOcrBackend:
    """Tests for the optional RapidOCR integration."""

    def test_rapid_ocr_line_to_words_single(self):
        """Single-word RapidOCR line should produce one word dict."""
        from tools.ocr import _rapid_ocr_on_image
        import numpy as np

        fake_engine = mock.MagicMock()
        fake_engine.return_value = (
            [
                [
                    [[10, 20], [110, 20], [110, 45], [10, 45]],
                    "Settings",
                    0.95,
                ],
            ],
            [0.1, 0.01, 0.5],
        )

        with mock.patch("tools.ocr._get_rapid_engine", return_value=fake_engine), \
             mock.patch("tools.ocr.Image") as mock_img:
            mock_pil = mock.MagicMock()
            mock_pil.size = (800, 600)
            mock_img.open.return_value = mock_pil
            mock_pil.close = mock.MagicMock()
            # Make np.array return a dummy array
            with mock.patch("tools.ocr._rapid_ocr_on_image.__module__", "tools.ocr"):
                pass

            # Call the function with mocked Image.open
            import tools.ocr as ocr_mod
            orig_get = ocr_mod._get_rapid_engine
            ocr_mod._get_rapid_engine = lambda: fake_engine
            try:
                with mock.patch.object(ocr_mod, "Image") as mock_img2:
                    mock_pil2 = mock.MagicMock()
                    mock_pil2.size = (800, 600)
                    mock_img2.open.return_value = mock_pil2
                    words = ocr_mod._rapid_ocr_on_image("/fake/test.png")
            finally:
                ocr_mod._get_rapid_engine = orig_get

        assert len(words) == 1
        assert words[0]["text"] == "Settings"
        assert words[0]["x"] == 10
        assert words[0]["y"] == 20
        assert words[0]["width"] == 100
        assert words[0]["height"] == 25

    def test_rapid_ocr_line_splits_into_words(self):
        """Multi-word RapidOCR line should be split into individual words."""
        import tools.ocr as ocr_mod

        fake_engine = mock.MagicMock()
        fake_engine.return_value = (
            [
                [
                    [[10, 20], [310, 20], [310, 45], [10, 45]],
                    "Save As PDF",
                    0.98,
                ],
            ],
            [0.1, 0.01, 0.5],
        )

        orig_get = ocr_mod._get_rapid_engine
        ocr_mod._get_rapid_engine = lambda: fake_engine
        try:
            with mock.patch.object(ocr_mod, "Image") as mock_img:
                mock_pil = mock.MagicMock()
                mock_pil.size = (800, 600)
                mock_img.open.return_value = mock_pil
                words = ocr_mod._rapid_ocr_on_image("/fake/test.png")
        finally:
            ocr_mod._get_rapid_engine = orig_get

        assert len(words) == 3
        assert words[0]["text"] == "Save"
        assert words[1]["text"] == "As"
        assert words[2]["text"] == "PDF"
        # Widths should sum to line width (300) proportional to char count
        total_w = sum(w["width"] for w in words)
        assert total_w == 300

    def test_rapid_ocr_low_confidence_filtered(self):
        """Results below confidence threshold should be filtered out."""
        import tools.ocr as ocr_mod

        fake_engine = mock.MagicMock()
        fake_engine.return_value = (
            [
                [[[10, 10], [60, 10], [60, 30], [10, 30]], "Good", 0.9],
                [[[70, 10], [120, 10], [120, 30], [70, 30]], "Bad", 0.1],  # below 0.3
            ],
            [0.1, 0.01, 0.5],
        )

        orig_get = ocr_mod._get_rapid_engine
        ocr_mod._get_rapid_engine = lambda: fake_engine
        try:
            with mock.patch.object(ocr_mod, "Image") as mock_img:
                mock_pil = mock.MagicMock()
                mock_pil.size = (800, 600)
                mock_img.open.return_value = mock_pil
                words = ocr_mod._rapid_ocr_on_image("/fake/test.png")
        finally:
            ocr_mod._get_rapid_engine = orig_get

        assert len(words) == 1
        assert words[0]["text"] == "Good"

    def test_dispatch_uses_rapid_ocr(self):
        """_run_ocr_engine should dispatch to _rapid_ocr_on_image."""
        import tools.ocr as ocr_mod

        with mock.patch.object(ocr_mod, "_rapid_ocr_on_image", return_value=[{"text": "Fast", "x": 1, "y": 1, "width": 20, "height": 10}]) as mock_rapid:
            result = ocr_mod._run_ocr_engine("/fake/test.png")

        assert result[0]["text"] == "Fast"
        mock_rapid.assert_called_once()

    def test_rapid_ocr_downscale_rescales_coords(self):
        """Oversized images should be downscaled and coords rescaled back."""
        import tools.ocr as ocr_mod

        fake_engine = mock.MagicMock()
        # Return word at (50, 25) in downscaled coords
        fake_engine.return_value = (
            [
                [[[50, 25], [90, 25], [90, 41], [50, 41]], "Hello", 0.95],
            ],
            [0.1, 0.01, 0.5],
        )

        orig_get = ocr_mod._get_rapid_engine
        ocr_mod._get_rapid_engine = lambda: fake_engine
        try:
            with mock.patch.object(ocr_mod, "Image") as mock_img:
                mock_pil = mock.MagicMock()
                mock_pil.size = (5120, 2160)  # Oversized
                resized = mock.MagicMock()
                mock_pil.resize.return_value = resized
                mock_img.open.return_value = mock_pil
                mock_img.LANCZOS = 1
                words = ocr_mod._rapid_ocr_on_image("/fake/large.png")
        finally:
            ocr_mod._get_rapid_engine = orig_get

        assert len(words) == 1
        # 5120 > 4096, scale_factor = 4096/5120 = 0.8, inv = 1.25
        assert words[0]["x"] > 50  # Should be rescaled up
        assert words[0]["text"] == "Hello"


class TestWindowScopedOcr:
    @mock.patch("tools.windows.do_list_windows", return_value=[
        {"title": "Notepad", "x": 100, "y": 50, "width": 800, "height": 600},
        {"title": "Edge - Reddit", "x": 900, "y": 0, "width": 1000, "height": 1080},
    ])
    def test_get_window_rect_returns_rect(self, _mock_list):
        """_get_window_rect should return a rect dict for a matching window."""
        from tools.ocr import _get_window_rect
        rect = _get_window_rect("Reddit")
        assert rect == {"x": 900, "y": 0, "w": 1000, "h": 1080}

    @mock.patch("tools.windows.do_list_windows", return_value=[
        {"title": "Notepad", "x": 100, "y": 50, "width": 800, "height": 600},
    ])
    def test_get_window_rect_returns_none_when_not_found(self, _mock_list):
        from tools.ocr import _get_window_rect
        rect = _get_window_rect("Firefox")
        assert rect is None

    @mock.patch("tools.windows.do_list_windows", return_value=[
        {"title": "Edge", "x": -8, "y": -8, "width": 1936, "height": 1096},
    ])
    def test_get_window_rect_clamps_negative_coords(self, _mock_list):
        """Negative x/y (common for maximized windows) should be clamped to 0."""
        from tools.ocr import _get_window_rect
        rect = _get_window_rect("Edge")
        assert rect["x"] == 0
        assert rect["y"] == 0

    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._get_window_rect", return_value={"x": 900, "y": 50, "w": 1000, "h": 1080})
    @mock.patch("tools.screenshot.capture_screenshot")
    @mock.patch("tools.target_window.get_target", return_value=None)
    def test_find_text_with_window_title_scopes_to_region(self, _mock_target, mock_cap, mock_rect, mock_ocr):
        """find_text with window_title should capture only that window's region."""
        mock_cap.return_value = {"path": "/fake/region.png", "width": 1000}
        mock_ocr.side_effect = [
            [{"text": "Showcase", "x": 50, "y": 200, "width": 80, "height": 20}],
            [],  # inverted pass
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Showcase", window_title="Reddit")
        assert len(result["matches"]) == 1
        # No downscaling (width == rect.w), coordinates should be offset: 50+900=950, 200+50=250
        assert result["matches"][0]["x"] == 950
        assert result["matches"][0]["y"] == 250

    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._capture_image_path", return_value="/fake/full.png")
    @mock.patch("tools.target_window.get_target", return_value=None)
    def test_find_text_without_window_title_scans_full_screen(self, _mock_target, _mock_cap, mock_ocr):
        """find_text without window_title should scan the full screen (existing behavior)."""
        mock_ocr.return_value = [
            {"text": "Hello", "x": 100, "y": 100, "width": 50, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Hello")
        # No offset — coordinates are screen-absolute already
        assert result["matches"][0]["x"] == 100

    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._get_window_rect", return_value={"x": 500, "y": 100, "w": 800, "h": 600})
    @mock.patch("tools.screenshot.capture_screenshot")
    def test_auto_scopes_to_target_window(self, mock_cap, mock_rect, mock_ocr):
        """When target_window is set and no explicit window_title, auto-scope."""
        mock_cap.return_value = {"path": "/fake/region.png", "width": 800}
        mock_ocr.side_effect = [
            [{"text": "Button", "x": 30, "y": 40, "width": 60, "height": 20}],
            [],  # inverted pass
        ]
        import tools.target_window as tw
        tw.set_target("Browser")
        try:
            from tools.ocr import do_find_text
            result = do_find_text("Button")
            assert result["matches"][0]["x"] == 530  # 30 + 500
            assert result["matches"][0]["y"] == 140  # 40 + 100
        finally:
            tw.set_target(None)

    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._capture_image_path", return_value="/fake/full.png")
    def test_explicit_window_title_overrides_target(self, _mock_cap, mock_ocr):
        """Explicit window_title should override any set target_window."""
        mock_ocr.return_value = []
        import tools.target_window as tw
        tw.set_target("Terminal")
        try:
            from tools.ocr import do_find_text
            with mock.patch("tools.ocr._get_window_rect", return_value=None) as mock_rect:
                do_find_text("test", window_title="Firefox")
                mock_rect.assert_called_with("Firefox")  # Not "Terminal"
        finally:
            tw.set_target(None)

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_click_text_passes_window_title(self, mock_find, mock_click):
        """click_text should pass window_title through to find_text."""
        mock_find.return_value = {
            "matches": [
                {"text": "OK", "x": 950, "y": 250, "width": 60, "height": 25},
            ]
        }
        mock_click.return_value = {"action": "click"}
        from tools.ocr import do_click_text
        do_click_text("OK", window_title="Dialog")
        mock_find.assert_called_once_with("OK", case_sensitive=False, window_title="Dialog", prefer_content=True, near_y=None)

    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._get_window_rect", return_value={"x": 2468, "y": 284, "w": 2219, "h": 1464})
    @mock.patch("tools.screenshot.capture_screenshot")
    @mock.patch("tools.target_window.get_target", return_value=None)
    def test_find_text_unscales_downscaled_region(self, _mock_target, mock_cap, mock_rect, mock_ocr):
        """When screenshot is downscaled for transport, OCR coords must be un-scaled."""
        # Window is 2219px wide but screenshot is downscaled to 1280px
        mock_cap.return_value = {"path": "/fake/region.png", "width": 1280}
        # OCR returns coordinates in 1280px space
        mock_ocr.side_effect = [
            [{"text": "Title", "x": 125, "y": 190, "width": 20, "height": 10}],
            [],  # inverted pass
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Title", window_title="Reddit")
        assert len(result["matches"]) == 1
        m = result["matches"][0]
        # scale = 2219/1280 ≈ 1.734
        # x should be round(125 * 1.734) + 2468 = 217 + 2468 = 2685
        # y should be round(190 * 1.734) + 284 = 329 + 284 = 613
        scale = 2219 / 1280
        assert m["x"] == round(125 * scale) + 2468
        assert m["y"] == round(190 * scale) + 284
        assert m["width"] == round(20 * scale)
        assert m["height"] == round(10 * scale)


class TestWindowScopeWarning:
    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._capture_image_path", return_value="/fake/full.png")
    @mock.patch("tools.target_window.get_target", return_value=None)
    @mock.patch("tools.windows.do_list_windows", return_value=[
        {"title": "Notepad", "x": 100, "y": 50, "width": 800, "height": 600},
    ])
    def test_warning_when_window_not_found(self, _mock_list, _mock_target, _mock_cap, mock_ocr):
        """When window_title is given but no window matches, include a warning."""
        mock_ocr.return_value = [
            {"text": "Hello", "x": 100, "y": 100, "width": 50, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Hello", window_title="Firefox")
        assert "window_scope_warning" in result
        assert "Firefox" in result["window_scope_warning"]
        assert "Notepad" in result["window_scope_warning"]

    @mock.patch("tools.ocr._run_ocr")
    @mock.patch("tools.ocr._get_window_rect", return_value={"x": 100, "y": 50, "w": 800, "h": 600})
    @mock.patch("tools.screenshot.capture_screenshot", return_value={"path": "/fake/region.png", "width": 800})
    @mock.patch("tools.target_window.get_target", return_value=None)
    def test_no_warning_when_window_found(self, _mock_target, _mock_cap, _mock_rect, mock_ocr):
        """When window matches successfully, no warning should be present."""
        mock_ocr.side_effect = [
            [{"text": "Hello", "x": 50, "y": 50, "width": 50, "height": 20}],
            [],  # inverted pass
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Hello", window_title="Notepad")
        assert "window_scope_warning" not in result


@mock.patch("tools.ocr._capture_image_path", return_value="/fake/screenshot.png")
class TestNearY:
    @mock.patch("tools.ocr._run_ocr")
    def test_near_y_sorts_by_proximity(self, mock_ocr, _mock_cap):
        """near_y should sort matches by distance to the target Y."""
        mock_ocr.return_value = [
            {"text": "Add", "x": 100, "y": 100, "width": 40, "height": 20},
            {"text": "Add", "x": 300, "y": 500, "width": 40, "height": 20},
            {"text": "Add", "x": 500, "y": 900, "width": 40, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("Add", near_y=480)
        assert len(result["matches"]) == 3
        # Closest to y=480: y=500 (center 510, dist=30), then y=100 (center 110, dist=370), then y=900 (center 910, dist=430)
        assert result["matches"][0]["y"] == 500
        assert result["matches"][1]["y"] == 100
        assert result["matches"][2]["y"] == 900

    @mock.patch("tools.ocr._run_ocr")
    def test_no_near_y_preserves_default_sort(self, mock_ocr, _mock_cap):
        """Without near_y, default content-area sort should apply."""
        mock_ocr.return_value = [
            {"text": "OK", "x": 100, "y": 900, "width": 40, "height": 20},
            {"text": "OK", "x": 100, "y": 100, "width": 40, "height": 20},
        ]
        from tools.ocr import do_find_text
        result = do_find_text("OK")
        assert len(result["matches"]) == 2
        # Without near_y, content-area score determines order (not necessarily y-order)

    @mock.patch("tools.ocr.do_click")
    @mock.patch("tools.ocr.do_find_text")
    def test_click_text_passes_near_y(self, mock_find, mock_click, _mock_cap):
        """click_text should pass near_y through to find_text."""
        mock_find.return_value = {
            "matches": [{"text": "Add", "x": 300, "y": 500, "width": 40, "height": 20}]
        }
        mock_click.return_value = {"action": "click"}
        from tools.ocr import do_click_text
        do_click_text("Add", near_y=500)
        mock_find.assert_called_once_with(
            "Add", case_sensitive=False, window_title=None,
            prefer_content=True, near_y=500,
        )


class TestRegister:
    def test_registers_two_tools(self):
        server = mock.MagicMock()
        from tools.ocr import register
        count = register(server)
        assert count == 2

