import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest


PROJECT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_DIR / "StellarHeal"


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=PROJECT_DIR / "tests")
        self.addCleanup(self.temp.cleanup)
        self.app_dir = Path(self.temp.name)
        shutil.copyfile(APP_DIR / "04_system_upgrade.py", self.app_dir / "app.py")
        (self.app_dir / "resources").mkdir()
        shutil.copyfile(APP_DIR / "resources" / "logo.png", self.app_dir / "resources" / "logo.png")
        self.create = Mock(side_effect=self.reply)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=self.create)))
        client_patch = patch("openai.OpenAI", return_value=client)
        client_patch.start()
        self.addCleanup(client_patch.stop)
        env_patch = patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-no-network"})
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.app = AppTest.from_file(self.app_dir / "app.py", default_timeout=15).run()
        self.assertFalse(self.app.exception)

    @staticmethod
    def reply(**kwargs):
        if kwargs.get("stream"):
            return iter([
                SimpleNamespace(choices=[]),
                SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="我在听，慢慢说。"))]),
            ])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="标题：工作压力疏导"))])

    def send(self, text="最近工作有些压力"):
        self.app.chat_input[0].set_value(text).run()
        self.assertFalse(self.app.exception)

    def title_calls(self):
        return [call for call in self.create.call_args_list if not call.kwargs.get("stream")]

    def records(self):
        return list((self.app_dir / "sessions").glob("*.json"))

    def test_auto_title_waits_two_rounds_and_runs_once(self):
        self.send()
        self.assertEqual(len(self.title_calls()), 0)
        self.assertEqual(self.app.session_state["session_title"], "新的对话")
        self.send("也影响到了睡眠")
        self.assertEqual(len(self.title_calls()), 1)
        self.assertEqual(self.app.session_state["session_title"], "工作压力疏导")
        self.send("谢谢")
        self.app.run()
        self.assertEqual(len(self.title_calls()), 1)
        self.assertEqual(json.loads(self.records()[0].read_text(encoding="utf-8"))["title"], "工作压力疏导")
        self.assertEqual([w.value for w in self.app.text_input if w.label == "会话标题"], ["工作压力疏导"])

    def test_off_blocks_generation_during_save_and_new_session(self):
        self.app.toggle(key="auto_title").set_value(False).run()
        self.send()
        self.send("第二条消息")
        self.app.button(key="save_session_btn").click().run()
        self.assertEqual(len(self.title_calls()), 0)
        self.assertEqual(self.app.session_state["session_title"], "新的对话")
        next(b for b in self.app.button if "新建会话" in b.label).click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.title_calls()), 0)
        self.assertFalse(self.app.session_state["auto_title"])
        self.assertEqual(self.app.session_state["messages"], [])

    def test_auto_title_works_without_auto_save(self):
        self.app.toggle(key="auto_save").set_value(False).run()
        self.send()
        self.send("第二条消息")
        self.assertEqual(len(self.title_calls()), 1)
        self.assertEqual(self.records(), [])
        self.app.button(key="save_session_btn").click().run()
        self.assertEqual(len(self.records()), 1)
        self.assertFalse(self.app.session_state["auto_save"])
        self.assertEqual(json.loads(self.records()[0].read_text(encoding="utf-8"))["title"], "工作压力疏导")

    def test_manual_generation_works_with_both_switches_off(self):
        self.app.toggle(key="auto_title").set_value(False).run()
        self.app.toggle(key="auto_save").set_value(False).run()
        self.send()
        self.app.button(key="auto_title_btn").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(self.title_calls()), 1)
        self.assertEqual(self.app.session_state["session_title"], "工作压力疏导")
        self.assertEqual(len(self.records()), 1)

    def test_manual_title_is_preserved_and_load_refreshes_editor(self):
        self.app.toggle(key="auto_title").set_value(False).run()
        self.send()
        next(w for w in self.app.text_input if w.label == "会话标题").set_value("我的小日记").run()
        self.app.button(key="update_title_btn").click().run()
        self.app.toggle(key="auto_title").set_value(True).run()
        self.send("第二条消息")
        self.assertEqual(self.app.session_state["session_title"], "我的小日记")
        self.assertEqual(len(self.title_calls()), 0)
        original_session = self.app.session_state["current_session"]
        next(b for b in self.app.button if "新建会话" in b.label).click().run()
        self.send("另一件事")
        self.app.button(key=f"load_{original_session}").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual([w.value for w in self.app.text_input if w.label == "会话标题"], ["我的小日记"])

    def test_enabling_title_for_existing_conversation(self):
        self.app.toggle(key="auto_title").set_value(False).run()
        self.send()
        self.send("第二条消息")
        self.app.toggle(key="auto_title").set_value(True).run()
        self.assertEqual(len(self.title_calls()), 1)
        self.app.run()
        self.assertEqual(len(self.title_calls()), 1)

    def test_failed_request_does_not_count_as_round(self):
        self.send()
        self.create.side_effect = RuntimeError("模拟网络中断")
        self.send("第二条消息")
        self.assertTrue(self.app.error)
        self.assertEqual(len(self.app.session_state["messages"]), 3)
        self.assertEqual(len(self.title_calls()), 0)
        self.assertEqual(self.app.session_state["session_title"], "新的对话")

    def test_failed_replace_preserves_old_record_and_title(self):
        self.app.toggle(key="auto_title").set_value(False).run()
        self.send()
        record = self.records()[0]
        original_bytes = record.read_bytes()
        next(w for w in self.app.text_input if w.label == "会话标题").set_value("新标题").run()
        with patch("os.replace", side_effect=OSError("模拟磁盘写入失败")):
            self.app.button(key="update_title_btn").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.error)
        self.assertEqual(record.read_bytes(), original_bytes)
        self.assertEqual(self.app.session_state["session_title"], "新的对话")
        self.assertEqual(list(record.parent.glob("*.tmp")), [])

    def test_missing_key_shows_error_without_crashing(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": ""}):
            self.send()
        self.assertTrue(self.app.error)
        self.assertEqual(len(self.app.session_state["messages"]), 1)

    def test_presets_keep_custom_inputs_in_sync(self):
        self.app.button(key="preset_倾听伙伴").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input(key="nick_name").value, "倾听伙伴")
        self.assertEqual(self.app.text_area(key="nature").value, "温暖、耐心、善于倾听")

    def test_batch_delete_reports_actual_results(self):
        directory = self.app_dir / "sessions"
        directory.mkdir()
        original_unlink = Path.unlink
        for failed_count in (0, 1, 2):
            with self.subTest(failed_count=failed_count):
                names = [f"2000-01-0{failed_count + 1} 00-00-0{i}" for i in range(2)]
                for name in names:
                    (directory / f"{name}.json").write_text(
                        json.dumps({"title": f"删除测试 {name[-1]}", "messages": []}), encoding="utf-8")
                failed_names = set(names[:failed_count])

                def unlink_with_failures(path, *args, **kwargs):
                    if path.stem in failed_names:
                        raise PermissionError("模拟文件被占用")
                    return original_unlink(path, *args, **kwargs)

                # 各场景独立启动页面，隔离已移除控件的测试状态。
                self.app = AppTest.from_file(self.app_dir / "app.py", default_timeout=15).run()
                self.app.multiselect[0].set_value(names).run()
                self.assertCountEqual(self.app.multiselect[0].value, names)
                with patch.object(Path, "unlink", unlink_with_failures):
                    next(b for b in self.app.button if "批量删除选中会话" in b.label).click().run()

                self.assertFalse(self.app.exception)
                self.assertEqual(len(self.app.error), failed_count, [error.value for error in self.app.error])
                self.assertTrue(all("模拟文件被占用" in error.value for error in self.app.error),
                                [error.value for error in self.app.error])
                successes = [message.value for message in self.app.success]
                self.assertEqual(successes, [f"已删除 {2 - failed_count} 个会话"] if failed_count < 2 else [])
                button_keys = [button.key for button in self.app.button]
                for name in names:
                    self.assertEqual((directory / f"{name}.json").exists(), name in failed_names)
                    self.assertEqual(f"load_{name}" in button_keys, name in failed_names)

    def test_single_delete_failure_preserves_conversation_and_shows_reason(self):
        self.send("需要保留的测试会话")
        record = self.records()[0]
        original_bytes = record.read_bytes()
        session_name = self.app.session_state["current_session"]
        for exception in (PermissionError("模拟文件被占用"), FileNotFoundError("模拟文件已被移除")):
            with self.subTest(exception=type(exception).__name__):
                with patch.object(Path, "unlink", side_effect=exception):
                    self.app.button(key=f"delete_{session_name}").click().run()
                self.assertFalse(self.app.exception)
                self.assertTrue(any(str(exception) in error.value for error in self.app.error))
                self.assertFalse(self.app.success)
                self.assertEqual(record.read_bytes(), original_bytes)
                self.assertEqual(self.app.session_state["current_session"], session_name)
                self.assertEqual(len(self.app.session_state["messages"]), 2)

    def test_single_delete_success_refreshes_history_and_current_session(self):
        self.send("可以删除的测试会话")
        record = self.records()[0]
        session_name = self.app.session_state["current_session"]
        self.app.button(key=f"delete_{session_name}").click().run()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.error)
        self.assertFalse(record.exists())
        self.assertEqual(self.app.session_state["messages"], [])
        self.assertNotEqual(self.app.session_state["current_session"], session_name)
        self.assertEqual([message.value for message in self.app.success], ["已删除 1 个会话"])
        self.assertNotIn(f"load_{session_name}", [button.key for button in self.app.button])


if __name__ == "__main__":
    unittest.main()
