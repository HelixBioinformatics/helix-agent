#!/usr/bin/python3
"""Refresh the thesis contents and export review copies with LibreOffice UNO.

Run with the system Python that provides `uno`. Uses an isolated temporary office
profile and a local named pipe. Does not open the user's running office session.
"""

import argparse
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

import uno
from com.sun.star.beans import PropertyValue


def prop(name, value):
    return PropertyValue(Name=name, Value=value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--rebuild-index", action="store_true", help="Replace the explicit thesis TOC marker with a native content index")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    target = args.directory.resolve() / args.source.name
    pdf = target.with_suffix(".pdf")
    if target.exists() or pdf.exists():
        parser.error("output files already exist; choose an empty review directory")
    pipe = "thesis_" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="thesis-office-") as profile:
        process = subprocess.Popen([
            "libreoffice", "-env:UserInstallation=" + Path(profile).as_uri(),
            "--headless", "--norestore", "--nodefault", "--nofirststartwizard",
            "--accept=pipe,name=" + pipe + ";urp;StarOffice.ComponentContext",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        document = None
        desktop = None
        try:
            local = uno.getComponentContext()
            resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
            deadline = time.monotonic() + 30
            while True:
                try:
                    context = resolver.resolve("uno:pipe,name=" + pipe + ";urp;StarOffice.ComponentContext")
                    break
                except Exception:
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("LibreOffice could not start or expose its local UNO pipe")
                    time.sleep(0.2)
            desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
            document = desktop.loadComponentFromURL(args.source.resolve().as_uri(), "_blank", 0, (
                prop("Hidden", True), prop("UpdateDocMode", 3),
                prop("MacroExecutionMode", uno.getConstantByName("com.sun.star.document.MacroExecMode.NEVER_EXECUTE")),
            ))
            if document is None:
                raise RuntimeError("LibreOffice did not load the thesis")
            if args.rebuild_index:
                search = document.createSearchDescriptor()
                search.SearchString = "THESIS_TOC_REBUILD_20260923"
                marker = document.findFirst(search)
                if marker is None:
                    raise RuntimeError("Missing explicit TOC reconstruction marker")
                cursor = document.getText().createTextCursorByRange(marker)
                index = document.createInstance("com.sun.star.text.ContentIndex")
                index.Title = ""
                index.CreateFromOutline = True
                index.CreateFromLevelParagraphStyles = False
                index.Level = 3
                document.getText().insertTextContent(cursor, index, True)
                index.update()
            # DOCX export can change imported paragraph/layout compatibility.
            # Reopen the intermediate Word so the delivered PDF matches its layout
            # when a reader opens it, including separation from the footer.
            for attempt in range(2):
                pass_docx = Path(profile) / "pagination-pass.docx" if attempt == 0 else target
                pass_pdf = Path(profile) / "pagination-pass.pdf" if attempt == 0 else pdf
                indexes = document.getDocumentIndexes()
                for index in range(indexes.getCount()):
                    item = indexes.getByIndex(index)
                    if item.supportsService("com.sun.star.text.ContentIndex"):
                        item.CreateFromOutline = True
                        # A heading selected both by outline and by an explicit style map
                        # is duplicated by Writer. All thesis headings have outline levels.
                        item.CreateFromLevelParagraphStyles = False
                        item.Level = 3
                    item.update()
                document.getTextFields().refresh()
                document.refresh()
                for index in range(indexes.getCount()):
                    indexes.getByIndex(index).update()
                document.getCurrentController().getViewCursor().jumpToLastPage()
                dispatcher = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.DispatchHelper", context)
                dispatcher.executeDispatch(document.getCurrentController().getFrame(), ".uno:UpdateAll", "", 0, ())
                # PDF export forces pagination. Refresh NUMPAGES only after that layout,
                # then save both formats with the same final field values.
                pdf_options = (
                    prop("FilterName", "writer_pdf_Export"),
                    # Keep Writer's section-parity pages so PDF length agrees with NUMPAGES.
                    prop("FilterData", uno.Any("[]com.sun.star.beans.PropertyValue", (prop("IsSkipEmptyPages", False),))),
                    prop("Overwrite", True),
                )
                document.storeToURL(pass_pdf.as_uri(), pdf_options)
                document.getTextFields().refresh()
                document.storeToURL(pass_docx.as_uri(), (prop("FilterName", "Office Open XML Text"),))
                document.storeToURL(pass_pdf.as_uri(), pdf_options)
                if attempt == 0:
                    document.close(True)
                    document = desktop.loadComponentFromURL(pass_docx.as_uri(), "_blank", 0, (
                        prop("Hidden", True), prop("UpdateDocMode", 3),
                        prop("MacroExecutionMode", uno.getConstantByName("com.sun.star.document.MacroExecMode.NEVER_EXECUTE")),
                    ))
                    if document is None:
                        raise RuntimeError("LibreOffice could not reopen the intermediate Word")
            print(f"Updated {indexes.getCount()} indexes; wrote {target} and {pdf}")
        finally:
            if document is not None:
                document.close(True)
            if desktop is not None:
                desktop.terminate()
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
