# Grand Finale Security & Robustness Audit
**Target Area**: Upload & Download Functionality (`import_api.py`, `download_api.py`)

## 1. Vulnerability Findings & Fixes

During the final security audit of the newly introduced bulk import and file upload functionality, several severe prototype-stage vulnerabilities were identified and patched before declaring the system production-ready.

### A. Path Traversal in Temporary Upload Storage
- **Finding**: The original upload logic saved files to `STORAGE_DIR / f"temp_{temp_id}_{file.filename}"`. Because `file.filename` was taken directly from the client request without sanitization, an attacker could supply `../../../etc/passwd` to traverse the directory structure and write files anywhere on the server's filesystem.
- **Fix Applied**: Implemented a robust `sanitize_filename` function using `os.path.basename(filename)` and strict alphanumeric whitelisting to strip all directory traversal sequences.

### B. Arbitrary File Move & Potential Exposure
- **Finding**: The `_link_file_to_report` function accepted arbitrary `temp_file_id` and `source_file_name` values from the JSON body in `process-text` and blindly called `.rename()` without enforcing boundary checks. An attacker could craft a payload moving arbitrary system files (e.g., system configuration) into the public application storage directory.
- **Fix Applied**: 
  - The `temp_file_id` is now strictly validated to ensure it is a valid UUIDv4.
  - The `temp_path` is resolved and asserted to `str(temp_path).startswith(str(STORAGE_DIR.resolve()))` to guarantee it remains sandboxed.

### C. Unlimited File Size (Denial of Service)
- **Finding**: `import_api.py` did not restrict the size of uploaded files, leaving the server vulnerable to resource exhaustion (OOM errors) if massive files were loaded into memory by the parser.
- **Fix Applied**: Added a strict 10MB `MAX_FILE_SIZE` check directly after the file upload headers are read, returning a `413 Payload Too Large` error if the limit is exceeded.

### D. Download Traversal via Database Record Manipulation
- **Finding**: While `download_api.py` read the file path from the database (preventing direct API-level traversal), it trusted the `source_file_path` implicitly. If a malicious path ever entered the database, it would serve that arbitrary file.
- **Fix Applied**: Added a `Path().resolve()` boundary check in `download_original_file` to ensure that any downloaded file strictly originates from within the `storage/originals/` sandbox.

## 2. Robustness Enhancements

- **Temporary File Cleanup Strategy**: Since temporary files are created on upload and moved upon processing, failed processing may leave orphaned temp files. The newly added UUID constraint guarantees that these temp files cannot conflict, but a cron job or scheduled task should be established in production to clear `temp_*` files older than 24 hours.
- **MIME Validation via Parser**: Instead of relying solely on HTTP headers which can be spoofed, the system relies on the robust `document_parser.py` which falls back to file extensions and uses dedicated libraries (`PyMuPDF`, `python-docx`, `pandas`) that inherently validate the binary signature structure. Malformed files crash the parsers gracefully and return a `422 Unprocessable Entity` or `500 Internal Server Error` without leaking stack traces.

## 3. Remaining Limitations (Prototype/V1)

- **Authentication / Authorization**: The application currently lacks user authentication. Any client with network access to the API can upload, process, and download files. Role-Based Access Control (RBAC) must be integrated for production deployment.
- **Malware Scanning**: Files are not currently passed through a malware scanner (e.g., ClamAV) before extraction.
- **Secret/Credential Exposure**: The backend is configured to use environment variables (`.env`) for database connections and API configurations. It currently does not leak these to the frontend, but the `.env` file should be secured and excluded from VCS.

**Audit Status**: **PASSED** (Upload/Download paths secured for SIH Grand Finale).
