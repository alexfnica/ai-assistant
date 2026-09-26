import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from jarvis.cloud_model import CloudModel, HybridModel
from jarvis.core import Core
from jarvis.documents import DocumentLibrary
from jarvis.integrations import Integrations, NotConnected
from jarvis.personality import load_prompt
from jarvis.storage import Store
from jarvis.tools import Toolbox
from jarvis.config import DEFAULTS

CT = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
WB = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
      '<sheet name="Stoc" sheetId="1" r:id="rId1"/><sheet name="DATE COMANDĂ" sheetId="2" r:id="rId2"/></sheets></workbook>')
RELS = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
SST = ('<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
       '<si><t>Specie</t></si><si><t>Ancistrus Bălțat</t></si><si><t>Client Secret Ion</t></si></sst>')
STYLES = ('<?xml version="1.0"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')
SHEET1 = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
          '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1"><v>12.5</v></c></row>'
          '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>7</v></c><c r="C2" s="1"><v>46023</v></c></row>'
          '</sheetData></worksheet>')
SHEET2 = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
          '<row r="1"><c r="A1" t="s"><v>2</v></c></row></sheetData></worksheet>')


def make_workbook(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("xl/workbook.xml", WB)
        z.writestr("xl/_rels/workbook.xml.rels", RELS)
        z.writestr("xl/sharedStrings.xml", SST)
        z.writestr("xl/styles.xml", STYLES)
        z.writestr("xl/worksheets/sheet1.xml", SHEET1)
        z.writestr("xl/worksheets/sheet2.xml", SHEET2)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        (self.dir / "docs").mkdir()
        make_workbook(self.dir / "docs" / "Stoc Acvariu.xlsx")
        self.store = Store(self.dir / "db.sqlite3")
        self.library = DocumentLibrary(self.dir / "docs", ["DATE COMANDĂ"])
        self.toolbox = Toolbox(self.store, self.library)


class DocumentTests(Base):
    def test_reads_values_dates_and_excludes_sheets(self):
        listing = self.library.list_documents()
        self.assertIn("Stoc [2 rows]", listing)
        self.assertNotIn("DATE COMAND", listing)
        text = self.library.read_sheet("stoc acvariu", "Stoc")
        self.assertIn("r2: Ancistrus Bălțat | 7 | 2026-01-01", text)
        self.assertIn("r1: Specie |  | 12.5", text)

    def test_search_is_accent_insensitive_and_skips_excluded_sheet(self):
        self.assertIn("Ancistrus", self.library.search("baltat"))
        self.assertEqual(self.library.search("secret"), "No matching rows were found.")

    def test_path_traversal_is_impossible(self):
        with self.assertRaises(ValueError):
            self.library.read_sheet("../db.sqlite3")


class FakeCloud(CloudModel):
    def __init__(self, store, toolbox, dir_, script):
        cfg = dict(DEFAULTS, monthly_token_budget=1000)
        super().__init__(store, toolbox, "sk-test-secret", cfg, dir_)
        self.script, self.calls = list(script), []

    def request(self, body):
        self.calls.append(json.loads(json.dumps(body)))
        return self.script.pop(0)


def text(t, usage=10):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": t}],
            "usage": {"input_tokens": usage, "output_tokens": usage}}


def tool(name, args, tid="t1"):
    return {"stop_reason": "tool_use", "usage": {"input_tokens": 5, "output_tokens": 5},
            "content": [{"type": "tool_use", "id": tid, "name": name, "input": args}]}


class CloudTests(Base):
    def test_tool_loop_reads_documents_and_counts_usage(self):
        cloud = FakeCloud(self.store, self.toolbox, self.dir,
                          [tool("search_documents", {"query": "ancistrus"}), text("Seven in stock, sir.")])
        answer = cloud.reply("How many Ancistrus?", "fishroom", system_prompt=load_prompt())
        self.assertEqual(answer, "Seven in stock, sir.")
        result = cloud.calls[1]["messages"][-1]["content"][0]
        self.assertEqual(result["type"], "tool_result")
        self.assertIn("Ancistrus Bălțat | 7", result["content"])
        self.assertEqual(cloud.meter.used(), 30)
        self.assertNotIn("sk-test-secret", json.dumps(cloud.calls))

    def test_budget_blocks_requests(self):
        cloud = FakeCloud(self.store, self.toolbox, self.dir, [text("x", usage=600)])
        cloud.reply("hi", "general", system_prompt="p")
        with self.assertRaises(NotConnected):
            cloud.reply("again", "general", system_prompt="p")

    def test_http_errors_do_not_leak(self):
        cloud = CloudModel(self.store, self.toolbox, "sk-live-secret", dict(DEFAULTS), self.dir)

        def boom(req, timeout=0):
            import urllib.error
            raise urllib.error.HTTPError("u", 401, "bad key sk-live-secret", {}, None)
        cloud.opener.open = boom
        with self.assertRaises(NotConnected) as ctx:
            cloud.reply("hi", "general", system_prompt="p")
        self.assertNotIn("sk-live-secret", str(ctx.exception))

    def test_hybrid_falls_back_to_local_with_note(self):
        class Local:
            state = "ready"
            def reply(self, *a, **k): return "local answer"
            def close(self): pass
        cloud = CloudModel(self.store, self.toolbox, "", dict(DEFAULTS), self.dir)
        self.assertEqual(HybridModel(cloud, Local()).reply("hi", "general", system_prompt="p"), "local answer")
        cloud2 = FakeCloud(self.store, self.toolbox, self.dir, [])
        cloud2.request = lambda body: (_ for _ in ()).throw(NotConnected("network down"))
        out = HybridModel(cloud2, Local()).reply("hi", "general", system_prompt="p")
        self.assertIn("local answer", out)
        self.assertIn("network down", out)


class ConfirmationTests(Base):
    def make_core(self, script):
        cloud = FakeCloud(self.store, self.toolbox, self.dir, script)
        return Core(self.store, Integrations(llm=HybridModel(cloud, None)))

    def test_proposal_is_saved_only_after_confirm(self):
        core = self.make_core([tool("propose_task", {"title": "Feed tank 5", "due_iso": "2026-09-27T18:00+03:00"}),
                               text("Shall I set it, sir? Say confirm.")])
        core.handle("remind me to feed tank 5 tomorrow at 6pm", "fishroom")
        self.assertEqual(self.store.tasks(), [])
        reply = core.handle("confirm", "fishroom")
        self.assertIn("Task #1 created", reply.text)
        task = self.store.tasks()[0]
        self.assertEqual((task["title"], task["module"]), ("Feed tank 5", "fishroom"))

    def test_cancel_discards_and_stale_confirm_does_nothing(self):
        core = self.make_core([tool("propose_note", {"text": "Idea"}), text("Noted for confirmation."),
                               text("Yes, I can help.")])
        core.handle("save an idea", "general")
        self.assertIn("discarded", core.handle("cancel", "general").text)
        self.assertEqual(self.store.memories(), [])
        self.assertIn("Yes, I can help", core.handle("yes", "general").text)
        self.assertEqual(self.store.memories(), [])

    def test_model_text_that_looks_like_a_command_is_inert(self):
        core = self.make_core([text("task: sneaky")])
        core.handle("plan my day", "general")
        self.assertEqual(self.store.tasks(), [])


if __name__ == "__main__":
    unittest.main()


class DocumentCommandTests(Base):
    def core(self):
        return Core(self.store, Integrations(docs=self.library))

    def test_free_commands_work_without_any_model(self):
        core = self.core()
        self.assertIn("Stoc Acvariu.xlsx", core.handle("documente").text)
        self.assertIn("Ancistrus Bălțat | 7", core.handle("open: stoc acvariu | Stoc").text)
        self.assertIn("Ancistrus", core.handle("search docs: baltat").text)
        self.assertIn("Ancistrus", core.handle("caută doc: BALTAT").text)
        self.assertIn("Stoc Acvariu", core.handle("show documents").text)

    def test_open_launches_only_listed_documents(self):
        core = self.core()
        opened = []
        self.library.launcher = opened.append
        self.assertIn("Opening Stoc Acvariu", core.handle("deschide stoc").text)
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].endswith("Stoc Acvariu.xlsx"))
        core.handle("open ../db.sqlite3")
        core.handle("open C:\\Windows\\system32\\calc.exe")
        self.assertEqual(len(opened), 1)
        self.assertIn("Ancistrus", core.handle("open: stoc | Stoc").text)  # colon form still shows rows

    def test_missing_folder_is_reported_honestly(self):
        reply = Core(self.store, Integrations()).handle("documente")
        self.assertIn("No documents folder", reply.text)


class BriefingTests(Base):
    def test_briefing_reports_tasks_and_survives_missing_documents(self):
        from jarvis.briefing import build_briefing, _ranges
        self.store.add_task("general", "Old thing", "2020-01-01T00:00:00+00:00")
        self.store.add_task("general", "No deadline")
        text = build_briefing(self.store, None)
        self.assertIn("Overdue (1): Old thing", text)
        self.assertIn("1 more open without a deadline", text)
        self.assertEqual(_ranges([1, 2, 3, 5, 7, 8]), "1–3, 5, 7–8")
        gone = DocumentLibrary(self.dir / "missing")
        self.assertIn("not reachable", build_briefing(self.store, gone))

    def test_briefing_command_and_aliases(self):
        core = Core(self.store, Integrations(docs=self.library))
        for phrase in ("briefing", "good morning", "Bună dimineața", "Jarvis, brief me"):
            self.assertIn("Shall we begin", core.handle(phrase).text)


class SpokenOpenTests(Base):
    def test_voice_phrases_find_the_right_file(self):
        make_workbook(self.dir / "docs" / "Stoc Acvariu - Categorii Separate.xlsx")
        make_workbook(self.dir / "docs" / "Tracker Vanzari Profit.xlsx")
        core = Core(self.store, Integrations(docs=self.library))
        opened = []
        self.library.launcher = opened.append
        for phrase, expected in (("open the stoc acvariu", "Stoc Acvariu.xlsx"), ("Open up my sales tracker in Excel please", "Tracker Vanzari Profit.xlsx"),
                                 ("open stocacvariu file", "Stoc Acvariu.xlsx"), ("deschide categorii separate", "Categorii Separate.xlsx")):
            opened.clear()
            reply = core.handle(phrase).text
            self.assertEqual(len(opened), 1, (phrase, reply))
            self.assertTrue(opened[0].endswith(expected), (phrase, opened))


class PoliteOpenTests(Base):
    def test_natural_requests_reach_the_document_commands_not_the_model(self):
        core = Core(self.store, Integrations(docs=self.library))
        opened = []
        self.library.launcher = opened.append
        for phrase in ("Can you open my Excel documents?", "Jarvis, please open the excel files", "open all my spreadsheets", "Could you open the stoc acvariu file please"):
            reply = core.handle(phrase).text
            self.assertNotIn("unable", reply.lower(), phrase)
        self.assertEqual(len(opened), 1)
        self.assertIn("Stoc Acvariu.xlsx", core.handle("can you open my Excel documents").text)


class SentenceIntentTests(Base):
    def test_any_open_excel_sentence_never_reaches_the_model(self):
        class Refuser:
            state = "ready"
            def reply(self, *a, **k): return "Sir, I'm sorry, but as an AI I cannot open files."
            def close(self): pass
        core = Core(self.store, Integrations(llm=Refuser(), docs=self.library))
        opened = []
        self.library.launcher = opened.append
        for phrase in ("I want you to open the documents on my computer in Excel", "Open Excel", "open the excel documents from my computer",
                       "Jarvis can you launch my spreadsheets", "open the stoc acvariu spreadsheet"):
            reply = core.handle(phrase).text
            self.assertNotIn("as an AI", reply, phrase)
        self.assertEqual(len(opened), 1)
        self.assertNotIn("Sir,\n\nSir", core.handle("hello there").text)
