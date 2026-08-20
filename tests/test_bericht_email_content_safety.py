from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


def function_body(name: str) -> str:
    marker = f"function {name}("
    start = HTML.index(marker)
    brace = HTML.index("{", start)
    depth = 0
    quote = None
    escaped = False
    template_depth = 0
    for pos in range(brace, len(HTML)):
        char = HTML[pos]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote and not (quote == "`" and template_depth):
                quote = None
            elif quote == "`" and char == "$" and HTML[pos : pos + 2] == "${":
                template_depth += 1
            elif quote == "`" and char == "}" and template_depth:
                template_depth -= 1
            continue
        if char in "'\"`":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return HTML[brace + 1 : pos]
    raise AssertionError(f"Unclosed function: {name}")


class BerichtEmailAndContentSafetyTests(unittest.TestCase):
    def test_canonical_version_is_3_11(self):
        self.assertIn("MadLeaf · v3.11", HTML)

    def test_main_report_text_is_explicit_and_empty_by_default(self):
        match = re.search(r'<textarea[^>]+id="bericht-text"[^>]*>(.*?)</textarea>', HTML, re.S)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "")
        self.assertIn("Durchgeführte Arbeiten *", HTML)

    def test_finalization_requires_meaningful_main_text(self):
        body = function_body("generatePDF")
        self.assertIn("validateFinalReport()", body)
        self.assertLess(body.index("validateFinalReport()"), body.index("buildPDF()"))
        validation = function_body("hasMeaningfulMainText")
        self.assertIn("text.length>=20", validation)
        self.assertIn("words.length>=3", validation)

    def test_preset_text_is_copied_into_visible_main_field(self):
        body = function_body("insertPresetIntoMainText")
        self.assertIn("querySelector('textarea')", body)
        self.assertIn("field.value=presetText", body)
        self.assertIn("hasMeaningfulMainText(presetText)", body)
        self.assertIn("insertPresetIntoMainText(b)", function_body("toggleA"))

    def test_preset_name_without_real_text_is_not_accepted(self):
        body = function_body("insertPresetIntoMainText")
        self.assertIn("if(!hasMeaningfulMainText(presetText)) return false", body)
        self.assertNotIn(".alabel", body)

    def test_manual_and_preset_text_use_the_same_validation(self):
        self.assertIn("hasMeaningfulMainText()", function_body("validateFinalReport"))
        self.assertIn("hasMeaningfulMainText(presetText)", function_body("insertPresetIntoMainText"))

    def test_deleting_generated_text_reenables_blocking(self):
        self.assertIn("addEventListener('input',onMainTextInput)", HTML)
        self.assertIn("delete field.dataset.presetText", function_body("onMainTextInput"))
        self.assertIn("if(!validateFinalReport()) return", function_body("generatePDF"))

    def test_draft_does_not_require_main_text(self):
        body = function_body("saveDraft")
        self.assertNotIn("validateFinalReport", body)
        self.assertIn("captureDraftPayload", body)

    def test_report_has_no_automatic_email_transport_or_embedded_key(self):
        forbidden = ("sendViaBrevo", "api.brevo.com", "BREVO_KEY", "MAIL_SERVER", "xkeysib-", "api-key")
        for value in forbidden:
            self.assertNotIn(value, HTML)

    def test_pdf_is_saved_before_optional_share_dialog(self):
        body = function_body("generatePDF")
        self.assertLess(body.index("doc.save(_lastFilename)"), body.index("openModal('m-send')"))
        self.assertNotIn("fetch(", body)
        self.assertNotIn("_stopTimer", body)

    def test_email_and_whatsapp_never_reset_or_claim_sent(self):
        for name in ("prepareEmail", "prepareWhatsApp"):
            body = function_body(name)
            self.assertNotIn("resetAll", body)
            self.assertNotIn("closeModal", body)
            self.assertNotIn("gesendet ✓", body)

    def test_reset_is_separate_and_confirmed(self):
        body = function_body("requestNewReport")
        self.assertIn("confirm(", body)
        self.assertIn("resetAll()", body)
        self.assertIn("Neuen Bericht beginnen", HTML)

    def test_draft_captures_content_timer_photos_and_signature(self):
        body = function_body("captureDraftPayload")
        for value in ("berichtText", "fotos", "signature", "timer", "prodotti", "actions"):
            self.assertIn(value, body)

    def test_drafts_are_reopenable_and_archive_stays_at_30(self):
        self.assertIn("Entwurf öffnen", HTML)
        self.assertIn("function loadDraft", HTML)
        body = function_body("saveDraft")
        self.assertIn("archiv.splice(30)", body)

    def test_old_archive_entries_remain_read_only_compatible(self):
        body = function_body("renderArchiv")
        self.assertIn("x.kind==='draft'&&x.draftId", body)
        self.assertIn("x.name", body)

    def test_bedbug_outcomes_remain_mutually_exclusive(self):
        self.assertEqual(HTML.count('data-group="bettwanzen-outcome"'), 3)
        body = function_body("toggleA")
        self.assertIn(".ablock[data-group=", body)

    def test_customer_change_still_does_not_reset_report(self):
        body = function_body("selectKunde")
        self.assertNotIn("resetAll", body)
        self.assertNotIn("bericht-text", body)

    def test_timer_restart_is_confirmed_and_immediately_running_from_zero(self):
        body = function_body("restartTimer")
        self.assertIn("Timer wirklich auf null setzen und neu starten?", body)
        self.assertIn("clearInterval(_timerInterval)", body)
        self.assertIn("_clearTimerPersistence()", body)
        self.assertIn("00h 00m 00s", body)
        self.assertIn("_timerStart=Date.now()", body)
        self.assertIn("setItem('ml_timer_elapsed','0')", body)
        self.assertIn("_startTimer()", body)

    def test_timer_restart_does_not_touch_report_content(self):
        body = function_body("restartTimer")
        for forbidden in ("resetAll", "state.kunde", "bericht-text", "prodotti", "fotos", "sig-k"):
            self.assertNotIn(forbidden, body)

    def test_running_timer_survives_page_reload(self):
        self.assertIn("restoreTimerState()", function_body("restoreTimerState") + function_body("_startTimer") + HTML[HTML.index("document.addEventListener('DOMContentLoaded'"):HTML.index("window.addEventListener('online'")])
        start = function_body("_startTimer")
        self.assertIn("setItem('ml_timer_running','1')", start)
        self.assertIn("setItem('ml_timer_started_at',String(_timerStart))", start)
        restore = function_body("restoreTimerState")
        self.assertIn("ml_timer_started_at", restore)
        self.assertIn("ml_timer_running", restore)
        self.assertIn("_startTimer()", restore)

    def test_new_report_resets_timer_atomically(self):
        body = function_body("_resetTimer")
        self.assertNotIn("_stopTimer", body)
        self.assertIn("_timerInterval=null", body)
        self.assertIn("_timerOn=false", body)
        self.assertIn("_timerStart=null", body)
        self.assertIn("_clearTimerPersistence()", body)
        persistence = function_body("_clearTimerPersistence")
        for key in ("ml_timer_elapsed", "ml_timer_running", "ml_timer_started_at"):
            self.assertIn(f"removeItem('{key}')", persistence)
        self.assertIn("00h 00m 00s", body)
        self.assertIn("resetAll()", function_body("requestNewReport"))

    def test_reopened_draft_restores_timer(self):
        body = function_body("restoreDraftPayload")
        self.assertIn("payload.timer?.elapsedMs", body)
        self.assertIn("payload.timer?.running", body)
        self.assertIn("_startTimer()", body)

    def test_mobile_breakpoint_is_preserved(self):
        self.assertIn('name="viewport"', HTML[:1000])
        self.assertIn("width:100%;max-width:480px", HTML)
        self.assertIn("max-width:90vw", HTML)
        self.assertIn("@media(max-width:420px)", HTML)
        self.assertIn(".btnmain,.btnshare", HTML)
        self.assertIn("min-width:0", HTML)

    def test_pdf_share_passes_a_real_pdf_file_to_native_share(self):
        body = function_body("sharePDF")
        self.assertIn("new File([doc.output('arraybuffer')]", body)
        self.assertIn("type:'application/pdf'", body)
        self.assertIn("navigator.canShare({files:[pdfFile]})", body)
        self.assertIn("navigator.share({files:[pdfFile]", body)

    def test_pdf_share_cancel_and_fallback_preserve_report(self):
        body = function_body("sharePDF")
        self.assertIn("shareError.name==='AbortError'", body)
        self.assertIn("doc.save(filename)", body)
        self.assertIn("bitte manuell anhängen", body)
        for forbidden in ("resetAll", "sendViaBrevo", "fetch(", "_stopTimer", "state="):
            self.assertNotIn(forbidden, body)

    def test_service_worker_cache_is_bumped(self):
        self.assertIn("madleaf-v11", SW)
        self.assertIn("self.skipWaiting()", SW)


if __name__ == "__main__":
    unittest.main()
