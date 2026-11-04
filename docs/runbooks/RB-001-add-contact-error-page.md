# RB-001: "Add contact" shows an error page and the contact is not saved

| | |
|---|---|
| **Applies to** | Venture CRM (Django + SQLite), running with `python manage.py runserver` |
| **Who this is for** | Anyone keeping the app running who did not write it. You need a terminal and the project folder (the one that contains `manage.py`). No Django knowledge needed. |
| **Time to fix** | Usually under 15 minutes |
| **Owner** | Roberta Henriquez (roberta.henriquez04@gmail.com). You should not need her to finish this. |
| **Last tested** | 2026-11-04. Every failure below was reproduced on purpose and every command was run. |

> **Two rules before you start**
> 1. **Never delete, rename or replace `db.sqlite3`.** It holds every contact, and it is *not* in Git, so there is no copy to get back from GitHub.
> 2. Do not run `manage.py migrate` until Step 3 tells you to. On the wrong file it builds empty tables, and it will look like every contact has been lost.

---

## 1. What you will see (the symptom)

A user reports one of these after filling in the form and clicking **Add contact**:

- A plain page saying **"Something went wrong"** with a **Reference code** such as `105e4d00498343b4`. *(This is the normal error page.)*
- A yellow Django page whose title starts with **`OperationalError at /`**. *(The app is running in debug mode, the default for this course project.)*
- Either of the above after the page **hangs for about 5 seconds**.

In every case the new contact is **not** in the list. Nothing was half-saved.

In the terminal running the server, or in the log file, you will see lines with `"level": "ERROR"` and `"status": 500`.

## 2. Find the failed request in the log

The log is one JSON object per line. It is written to the terminal running the server **and** to `logs/venture-crm.jsonl` inside the project folder. Older lines rotate into `venture-crm.jsonl.1` ... `.5`.

Open a **second** terminal (leave the server running), `cd` into the project folder, and run:

```
python scripts/logq.py --failed
```

You get one line per failed request, newest last. Example:

```
2026-11-04T20:35:42.004Z  ERROR   request.end   rid=578031ba4bd44e64  method="POST"  path="/"  status=500  duration_ms=5017.3
```

`rid` is the **request_id**. It is the same value as the user's **Reference code**. If the user gave you a code, use it. If not, pick the failed request whose time matches their report (times are **UTC**; US Central is UTC − 6 hours in winter, − 5 in summer).

Now show everything that request did:

```
python scripts/logq.py 578031ba4bd44e64
```

## 3. Confirm which failure it is

Read the `error=` value in the output from Step 2. It appears on the `contact.create.failed` line, on the `django.request` line, or on both. Find the matching row:

| `error=` says | Does the contact list page (`http://127.0.0.1:8000/`) still load? | Go to |
|---|---|---|
| `attempt to write a readonly database` | **Yes.** Only saving fails, and it fails instantly. | **3A** |
| `database is locked` (and `db_ms` is about `5000`) | **Yes**, but saving hangs about 5 s, then fails | **3B** |
| `no such table: tracker_contact` | **No.** The list page fails too. | **3C** |
| anything else | | **Section 5 (escalate)** |

<details><summary>What the full trace looks like (case 3A)</summary>

```
2026-11-04T20:35:01.694Z  INFO    request.start            rid=105e4d00498343b4  method="POST"  path="/"
2026-11-04T20:35:01.709Z  ERROR   contact.create.failed    rid=105e4d00498343b4  error_type="OperationalError"  error="attempt to write a readonly database"  db_ms=0.7
2026-11-04T20:35:01.710Z  ERROR   django.request           rid=105e4d00498343b4  msg="Internal Server Error: /"  error_type="OperationalError"  error="attempt to write a readonly database"  stack="... django.db.utils.OperationalError: attempt to write a readonly database"
2026-11-04T20:35:01.718Z  ERROR   request.end              rid=105e4d00498343b4  method="POST"  path="/"  status=500  duration_ms=23.8
```
</details>

**Before any fix, make a backup copy** (it copies, it does not move). For **3B**, wait until after the lock is released.

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `cp db.sqlite3 "db.sqlite3.bak-$(date +%Y%m%d-%H%M)"` | `Copy-Item db.sqlite3 "db.sqlite3.bak-$(Get-Date -Format yyyyMMdd-HHmm)"` |

### 3A. "attempt to write a readonly database"

**Meaning:** the app can read the database file but is not allowed to change it. SQLite also needs to write a temporary journal file *next to* `db.sqlite3`, so a read-only **folder** causes the same error. Common triggers: the file was copied or restored from somewhere else, it was created by a different user (for example a command once run with `sudo`), or a sync tool (OneDrive, iCloud, Dropbox) has marked it read-only.

**Confirm:**

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `ls -l db.sqlite3` then `ls -ld .` | `attrib db.sqlite3` |
| Look for a missing `w` in the first block (e.g. `-r--r--r--`), or an owner that is not you. | An `R` in the output means read-only. |

**Fix:**

| macOS / Linux | Windows (PowerShell) |
|---|---|
| `chmod u+w db.sqlite3` and `chmod u+w .` | `attrib -R db.sqlite3` |
| If the owner is not you: `sudo chown "$USER" db.sqlite3` | If the folder is inside OneDrive: right-click the project folder, choose **Always keep on this device**, and wait for sync to finish. |

Do **not** use `chmod 777`. You do not need to restart the server. Go to **Section 4**.

### 3B. "database is locked"

**Meaning:** another program has started changing the database and has not finished, so the app waits 5 seconds for it and then gives up. Reading still works, which is why the list page loads. The usual cause is **DB Browser for SQLite** (or a similar viewer) with **unsaved edits**. Other causes: a `python manage.py shell` or `dbshell` session left open, or a **second** copy of the server running on the same folder.

**Confirm:**

| macOS / Linux | Windows |
|---|---|
| `lsof db.sqlite3` lists every program that has the file open. Any program other than the one server (`python ... runserver`) is the suspect. | Open **Resource Monitor** (search for `resmon`), go to the **CPU** tab, and type `db.sqlite3` into **Associated Handles**. |

**Fix (in this order):**
1. **DB Browser for SQLite** (or similar): click **Write Changes** if you made those edits on purpose. If you don't know who made them, click **Revert Changes** (this only throws away the viewer's unsaved edits, not the app's data). Then close it.
2. Close any open `manage.py shell` / `dbshell` window by typing `exit()` or pressing Ctrl+D (Ctrl+Z then Enter on Windows).
3. If two servers are running, stop the extra one with Ctrl+C in its terminal.

Do **not** force-quit (kill) the program holding the lock unless steps 1-3 are impossible. Go to **Section 4**.

### 3C. "no such table: tracker_contact"

**Meaning:** the app opened a database file that has no contact table. The whole site is down, not just saving. Usually `db.sqlite3` was deleted, moved, or replaced, and SQLite silently created a new **empty** file with the same name. Or this is a fresh copy of the project where setup was never run.

**Confirm:**

```
python manage.py showmigrations tracker
```

`[ ] 0001_initial` (empty box) means the table was never created in this file. Also check the size of `db.sqlite3` (`ls -l db.sqlite3` or `dir db.sqlite3`). **0 bytes** means it is a brand-new empty file.

**Fix:**
- **If contacts were stored here before:** the real database is somewhere else. Stop the server (Ctrl+C), then look for it: a `db.sqlite3.bak-*` copy, the Recycle Bin or Trash, or another copy of the project folder. Copy it back to `db.sqlite3`, start the server again, and **do not run migrate**. If you cannot find it, **stop here and escalate** (Section 5).
- **If this really is a new install with no contacts yet:** run `python manage.py migrate`. Then go to Section 4.

## 4. Check that it is fixed

1. Open `http://127.0.0.1:8000/` and add a contact named **Runbook Check** (any stage). It should appear at the top of the list.
2. Confirm the log shows success: run `python scripts/logq.py --last 6` and look for `contact.created` followed by `request.end` with `status=302`.
3. Remove the test contact:
   ```
   python manage.py shell -c "from tracker.models import Contact; print(Contact.objects.filter(name='Runbook Check').delete())"
   ```
4. **Tell the user** that the contacts they tried to add while it was broken were **not saved** and need to be entered again.

## 5. Escalate if

- the error is not one of the three in Step 3,
- the fix did not work (Section 4, step 1 still fails), or
- you could not find the real database in 3C.

Leave the server and the files exactly as they are. Save the evidence to a file:

```
python scripts/logq.py --last 50 > incident-evidence.txt
```

Email `incident-evidence.txt` to the owner (top of this page), with the user's reference code and roughly what time it happened. In the meantime, tell users that adding contacts is unavailable. Nothing they already saved is lost.

---

*Background for the curious (you don't need this to fix it):* every log line has the same first five fields: `ts`, `level`, `logger`, `event`, `request_id`. Each request gets one `request_id`. It is attached to every line written while handling that request, returned in the `X-Request-ID` response header, and shown to users as the reference code. See `tracker/observability.py`.
