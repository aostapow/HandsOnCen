# tests/test_batch.py
"""Tests for the batch actions tool."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "handson-server"),
)


class TestBatchActions:
    @mock.patch("tools.batch.do_send_keys")
    @mock.patch("tools.batch.do_type_text")
    @mock.patch("tools.batch.do_click")
    def test_click_type_keys_sequence(self, mock_click, mock_type, mock_keys):
        mock_click.return_value = {"action": "click", "x": 100, "y": 200, "button": "left", "clicks": 1}
        mock_type.return_value = {"action": "type_text", "text": "hello", "interval": 0.02, "method": "pyautogui"}
        mock_keys.return_value = {"action": "send_keys", "keys": "enter", "method": "pyautogui"}

        from tools.batch import do_batch_actions
        result = do_batch_actions([
            {"action": "click", "x": 100, "y": 200},
            {"action": "type", "text": "hello"},
            {"action": "keys", "keys": "enter"},
        ])

        assert result["success"] is True
        assert result["executed"] == 3
        mock_click.assert_called_once_with(100, 200, button="left", clicks=1)
        mock_type.assert_called_once_with("hello", interval=0.02)
        mock_keys.assert_called_once_with("enter")

    @mock.patch("tools.batch.do_click")
    def test_click_with_options(self, mock_click):
        mock_click.return_value = {"action": "click", "x": 50, "y": 60, "button": "right", "clicks": 2}

        from tools.batch import do_batch_actions
        result = do_batch_actions([
            {"action": "click", "x": 50, "y": 60, "button": "right", "clicks": 2},
        ])

        mock_click.assert_called_once_with(50, 60, button="right", clicks=2)

    @mock.patch("tools.batch.time.sleep")
    def test_wait_action(self, mock_sleep):
        from tools.batch import do_batch_actions
        result = do_batch_actions([
            {"action": "wait", "ms": 500},
        ])
        mock_sleep.assert_called_once_with(0.5)
        assert result["executed"] == 1

    @mock.patch("tools.batch.do_scroll")
    def test_scroll_action(self, mock_scroll):
        mock_scroll.return_value = {"action": "scroll", "x": 300, "y": 400, "direction": "down", "amount": 3}

        from tools.batch import do_batch_actions
        result = do_batch_actions([
            {"action": "scroll", "x": 300, "y": 400, "direction": "down", "amount": 5},
        ])
        mock_scroll.assert_called_once_with(300, 400, "down", amount=5, pages=None)

    def test_invalid_action_fails(self):
        from tools.batch import do_batch_actions
        result = do_batch_actions([
            {"action": "explode"},
        ])
        assert result["success"] is False
        assert "Unknown action" in result["error"]

    def test_empty_list_succeeds(self):
        from tools.batch import do_batch_actions
        result = do_batch_actions([])
        assert result["success"] is True
        assert result["executed"] == 0

    @mock.patch("tools.batch.do_click")
    def test_missing_required_field_fails(self, mock_click):
        from tools.batch import do_batch_actions
        result = do_batch_actions([
            {"action": "click", "x": 100},  # missing y
        ])
        assert result["success"] is False


class TestRegister:
    def test_registers_one_tool(self):
        server = mock.MagicMock()
        from tools.batch import register
        count = register(server)
        assert count == 1
