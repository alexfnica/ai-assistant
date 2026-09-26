"""Minimal read-only .xlsx reader using only the standard library.

It returns the cached (last saved) cell values, like openpyxl's data_only mode.
Formulas are never evaluated and nothing is written back to the workbook.
"""
import re
import zipfile
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DATE_IDS = set(range(14, 23)) | {27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 45, 46, 47, 50, 51, 52, 53, 54, 55, 56, 57, 58}
DATE_TOKENS = re.compile(r"[dmyhs]", re.IGNORECASE)
MAX_XML = 80 * 1024 * 1024  # refuse decompression bombs


class XlsxError(ValueError):
    pass


def _read(archive, name):
    info = archive.getinfo(name)
    if info.file_size > MAX_XML:
        raise XlsxError("Workbook part is too large to read safely.")
    return archive.read(name)


def _column(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    number = 0
    for char in letters:
        number = number * 26 + ord(char) - 64
    return number - 1


def _shared_strings(archive):
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(_read(archive, "xl/sharedStrings.xml"))
    strings = []
    for si in root.iter(NS + "si"):
        parts = []
        for child in si:
            if child.tag == NS + "t":
                parts.append(child.text or "")
            elif child.tag == NS + "r":
                parts.extend(t.text or "" for t in child.findall(NS + "t"))
        strings.append("".join(parts))
    return strings


def _date_styles(archive):
    if "xl/styles.xml" not in archive.namelist():
        return set()
    root = ET.fromstring(_read(archive, "xl/styles.xml"))
    custom = {}
    formats = root.find(NS + "numFmts")
    if formats is not None:
        for fmt in formats:
            code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", fmt.get("formatCode", ""))
            custom[int(fmt.get("numFmtId"))] = bool(DATE_TOKENS.search(code))
    styles = set()
    xfs = root.find(NS + "cellXfs")
    if xfs is not None:
        for index, xf in enumerate(xfs):
            fmt_id = int(xf.get("numFmtId", "0"))
            if fmt_id in DATE_IDS or custom.get(fmt_id):
                styles.add(index)
    return styles


def _sheet_targets(archive):
    workbook = ET.fromstring(_read(archive, "xl/workbook.xml"))
    rels = ET.fromstring(_read(archive, "xl/_rels/workbook.xml.rels"))
    targets = {}
    for rel in rels.findall(PKG_REL + "Relationship"):
        target = rel.get("Target", "").lstrip("/")
        targets[rel.get("Id")] = target if target.startswith("xl/") else "xl/" + target
    sheets = []
    container = workbook.find(NS + "sheets")
    for sheet in (container if container is not None else []):
        path = targets.get(sheet.get(REL + "id"))
        if path and path in archive.namelist():
            sheets.append((sheet.get("name", "Sheet"), path, sheet.get("state") == "hidden"))
    return sheets


def _number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return text or ""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return ("%.6g" % value)


def _date(text):
    try:
        value = float(text)
        moment = datetime(1899, 12, 30) + timedelta(days=value)
    except (TypeError, ValueError, OverflowError):
        return text or ""
    return moment.strftime("%Y-%m-%d") if value == int(value) else moment.strftime("%Y-%m-%d %H:%M")


def _cell_value(cell, strings, date_styles):
    kind = cell.get("t")
    if kind == "inlineStr":
        node = cell.find(NS + "is")
        return "".join(t.text or "" for t in node.iter(NS + "t")) if node is not None else ""
    node = cell.find(NS + "v")
    text = node.text if node is not None else None
    if text is None:
        return ""
    if kind == "s":
        try:
            return strings[int(text)]
        except (ValueError, IndexError):
            return ""
    if kind == "b":
        return "TRUE" if text == "1" else "FALSE"
    if kind in ("str", "e"):
        return text
    if int(cell.get("s", "0") or 0) in date_styles:
        return _date(text)
    return _number(text)


def _sheet_rows(archive, path, strings, date_styles, max_rows):
    rows = {}
    stream = archive.open(path)
    try:
        for _event, element in ET.iterparse(stream, events=("end",)):
            if element.tag != NS + "row":
                continue
            number = int(element.get("r", "0") or 0)
            if number and number <= max_rows:
                cells = {}
                for cell in element.findall(NS + "c"):
                    ref = cell.get("r")
                    if not ref:
                        continue
                    value = _cell_value(cell, strings, date_styles)
                    if value != "":
                        cells[_column(ref)] = value
                if cells:
                    width = max(cells) + 1
                    rows[number] = [cells.get(i, "") for i in range(width)]
            element.clear()
            if number > max_rows:
                break
    finally:
        stream.close()
    return rows


def read_workbook(path, max_rows=3000):
    """Return {sheet_name: {row_number: [cell text, ...]}} for visible sheets."""
    try:
        with zipfile.ZipFile(path) as archive:
            strings = _shared_strings(archive)
            date_styles = _date_styles(archive)
            result = {}
            for name, part, hidden in _sheet_targets(archive):
                if hidden:
                    continue
                result[name] = _sheet_rows(archive, part, strings, date_styles, max_rows)
            return result
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as error:
        raise XlsxError("The workbook could not be read: " + type(error).__name__) from None
